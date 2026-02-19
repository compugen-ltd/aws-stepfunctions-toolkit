from __future__ import annotations

import os
import logging
import json
import uuid
from abc import ABC, abstractmethod
from typing import Final, TypedDict, NotRequired, TYPE_CHECKING
import tempfile
from pathlib import Path
import base64

import boto3
from python_on_whales import docker
from mypy_boto3_stepfunctions.type_defs import MockInputTypeDef
from mypy_boto3_appconfigdata import AppConfigDataClient
from mypy_boto3_batch.client import BatchClient
from mypy_boto3_batch.type_defs import ContainerOverridesTypeDef, KeyValuePairTypeDef
from mypy_boto3_s3.client import S3Client


if TYPE_CHECKING:
    from .workflow_runner import WorkflowRunner

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

RESOURCE_OUTPUT_PATTERNS: Final[dict[str, tuple[str, str]]] = {
    "arn:aws:states:::states:startExecution.sync:2": ("$states.result.Output", "$parse($states.result.Output)"),
    "arn:aws:states:::lambda:invoke": ("$states.result.Payload", "$parse($states.result.Payload)"),
}

TestStateInputTypeDef = TypedDict(
    "TestStateInputTypeDef",
    {
        "mock": NotRequired[MockInputTypeDef],
    },
)

TestStateInputTypeDefSlim = TypedDict(
    "TestStateInputTypeDefSlim",
    {
        "mock": NotRequired[MockInputTypeDef],
        "context": NotRequired[str],
    },
)


def login_to_ecr(region="us-east-1"):
    """Authenticate to ECR using python_on_whales"""
    ecr_client = boto3.client('ecr', region_name=region)

    # Get authorization token from ECR
    response = ecr_client.get_authorization_token()
    auth_data = response['authorizationData'][0]

    # Decode the token (format is "username:password")
    token = base64.b64decode(auth_data['authorizationToken']).decode()
    username, password = token.split(':')

    # Get the registry URL
    registry = auth_data['proxyEndpoint'].replace('https://', '')

    # Login using python_on_whales
    docker.login(
        server=registry,
        username=username,
        password=password
    )

    print(f"Successfully logged in to {registry}")
    return registry


# --- 1. Execution Strategy Interface ---
class StateExecutionStrategy(ABC):
    @abstractmethod
    def execute(self, state_name: str, state_def: dict, input_data: dict, orchestrator: WorkflowRunner,
                context: str = None, parent_path: str = "") -> TestStateInputTypeDefSlim:
        """Should return a dict (the raw result) or None if test_state should handle it."""
        pass


class BatchImageStrategy(StateExecutionStrategy):
    def __init__(self, s3_bucket, image: str, execution_id=None, volumes=None, variables=None,
                 user=None):
        self.s3_bucket = s3_bucket
        self.execution_id = execution_id or f"test-{uuid.uuid4().hex[:6]}"
        self.s3_client: S3Client = boto3.client('s3')
        self.image = image
        self.volumes = volumes
        self.variables = variables or dict()
        self.user = user
        login_to_ecr()

    def _get_after_arguments_overrides(self, orchestrator, state_def, input_data, context):
        response = orchestrator.client.test_state(
            definition=json.dumps(state_def),
            roleArn=orchestrator.role_arn,
            variables=json.dumps(self.variables),
            input=json.dumps(input_data),
            inspectionLevel="TRACE",
            context=context,
            mock={
                'result': json.dumps({}),
                "fieldValidationMode": "PRESENT"
            }
        )
        return json.loads(response["inspectionData"]["afterArguments"])["ContainerOverrides"]

    def _build_and_run_image(self, command, s3_out, extra_envs: dict):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chmod(tmpdir, 0o777)  # drwxrwxrwx
            output_path = "/tmp/output.json"
            docker.run(
                image=self.image,
                command=command,
                envs={"S3_OUTPUT_PATH": s3_out, "OUTPUT_PATH": output_path} | extra_envs,
                remove=True,
                user=self.user,
                volumes=self.volumes + [(str(tmpdir), "/tmp", "rw")],
            )
            data = Path(tmpdir).joinpath("output.json").read_text()
        return data

    def execute(self, state_name, state_def, input_data, orchestrator, context=None, parent_path=""):
        s3_out = f"s3://{self.s3_bucket}/{self.execution_id}/{state_name}/output.json"

        overrides = self._get_after_arguments_overrides(orchestrator, state_def, input_data, context)
        command = overrides["Command"]
        envs = {ele["Name"]: ele["Value"] for ele in overrides["Environment"]}
        _ = envs.pop("TaskToken")
        data = self._build_and_run_image(command, s3_out, envs)

        return {"mock": {"result": data}, "context": context}


# --- 2. Implementation: Batch Strategy ---
class LocalBatchImageStrategy(StateExecutionStrategy):
    def __init__(self, s3_bucket, target_name, bake_file, execution_id=None, volumes=None, variables=None,
                 user=None, base_dir:str=None):
        self.s3_bucket = s3_bucket
        self.execution_id = execution_id or f"test-{uuid.uuid4().hex[:6]}"
        self.target_name = target_name
        self.bake_file = bake_file
        self.s3_client: S3Client = boto3.client('s3')
        # self.volumes = [(temp.name, "/Rnd/supplementary/GSE15471/GSE15471.h5ad")]
        self.volumes = volumes
        self.variables = variables or dict()
        self.user = user
        self.base_dir=base_dir

    def _get_after_arguments_overrides(self, orchestrator, state_def, input_data, context):
        response = orchestrator.client.test_state(
            definition=json.dumps(state_def),
            roleArn=orchestrator.role_arn,
            variables=json.dumps(self.variables),
            input=json.dumps(input_data),
            inspectionLevel="TRACE",
            context=context,
            mock={
                'result': json.dumps({}),
                "fieldValidationMode": "PRESENT"
            }
        )
        return json.loads(response["inspectionData"]["afterArguments"])["ContainerOverrides"]

    def _build_and_run_image(self, command, s3_out, extra_envs: dict):
        docker.buildx.bake(
            targets=[self.target_name],
            files=[self.bake_file],
            variables={
                "BASE_DIR": str(self.base_dir)
            },
            set={
                "*.tags": f"{self.target_name}:latest",
                "*.args.ENVIRONMENT": "dev",
            },
            load=False
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chmod(tmpdir, 0o777)  # drwxrwxrwx
            output_path = "/tmp/output.json"
            docker.run(
                image=self.target_name,
                command=command,
                envs={"S3_OUTPUT_PATH": s3_out, "OUTPUT_PATH": output_path} | extra_envs,
                remove=True,
                user=self.user,
                volumes=self.volumes + [(str(tmpdir), "/tmp", "rw")],
            )
            data = Path(tmpdir).joinpath("output.json").read_text()
        return data

    def execute(self, state_name, state_def, input_data, orchestrator, context=None, parent_path=""):
        target = self.target_name
        s3_out = f"s3://{self.s3_bucket}/{self.execution_id}/{state_name}/output.json"
        os.environ["BUILDX_BAKE_ENTITLEMENTS_FS"] = "0"
        print(f"🏗️  Batch: Baking & Running {target}")

        overrides = self._get_after_arguments_overrides(orchestrator, state_def, input_data, context)
        command = overrides["Command"]
        envs = {ele["Name"]: ele["Value"] for ele in overrides["Environment"]}
        _ = envs.pop("TaskToken")
        data = self._build_and_run_image(command, s3_out, envs)

        return {"mock": {"result": data}, "context": context}


# --- 3. Implementation: Static Mock Strategy ---
class GetLatestConfigurationStrategy(StateExecutionStrategy):
    def __init__(self, appconfigdata_client: AppConfigDataClient = None):
        if not appconfigdata_client:
            appconfigdata_client = boto3.client("appconfigdata", region_name="us-east-1")
        self.appconfigdata_client = appconfigdata_client

    def execute(self, state_name, state_def, input_data, orchestrator, context: str = "{}", parent_path=""):
        appconfigdata_client = self.appconfigdata_client
        response = appconfigdata_client.start_configuration_session(
            ApplicationIdentifier="unigen_pipeline",
            EnvironmentIdentifier="test",
            ConfigurationProfileIdentifier="db",
        )

        response = appconfigdata_client.get_latest_configuration(
            ConfigurationToken=response["InitialConfigurationToken"],
        )

        data = response["Configuration"].read().decode("utf8")
        kwargs = {
            "mock": {'result': data},
            "context": context
        }
        return kwargs


class StaticMockResponseStrategy(StateExecutionStrategy):
    def __init__(self, result: str):
        self.result = result

    def execute(self, state_name, state_def, input_data, orchestrator, context=None, parent_path=""):
        kwargs = {
            "mock": {'result': self.result},
            "context": context
        }
        return kwargs


class BatchJobResponseStrategy(StateExecutionStrategy):
    def __init__(self, job_queue: str, job_definition: str, job_name: str = None, batch_client: BatchClient = None,
                 variables: dict = None):
        if not batch_client:
            batch_client = boto3.client("batch", region_name="us-east-1")
        self.client = batch_client
        self.job_queue = job_queue
        self.job_name = job_name or "sometestjob"
        self.job_definition = job_definition
        self.variables = variables or {}

    def _get_after_arguments_overrides(self, orchestrator, state_def, input_data, context) -> dict:
        response = orchestrator.client.test_state(
            definition=json.dumps(state_def),
            roleArn=orchestrator.role_arn,
            variables=json.dumps(self.variables),
            input=json.dumps(input_data),
            inspectionLevel="TRACE",
            context=context,
            mock={
                'result': json.dumps({}),
                "fieldValidationMode": "PRESENT"
            }
        )
        return json.loads(response["inspectionData"]["afterArguments"])["ContainerOverrides"]

    def execute(self, state_name, state_def, input_data, orchestrator, context=None, parent_path=""):
        container_overrides = self._get_after_arguments_overrides(orchestrator, state_def, input_data, context)
        environment = [
            KeyValuePairTypeDef(name=env["Name"], value=env["Value"])
            for env in container_overrides["Environment"]
        ]

        _ = self.client.submit_job(
            jobName=self.job_name,
            jobQueue=self.job_queue,
            jobDefinition=self.job_definition,
            containerOverrides=ContainerOverridesTypeDef(
                environment=environment,
                command=container_overrides["Command"]
            )
        )
        # Wait for task to end successfully
        # Can also run this as a local image
        # Read data from s3

        # TODO: get results from s3
        # return

        return {}


class AbstractMockMapResponseStrategy(StateExecutionStrategy, ABC):

    @abstractmethod
    def get_items(self, input_data):
        pass

    def execute(self, state_name: str, state_def: dict, input_data: dict, orchestrator: WorkflowRunner,
                context: str = None, parent_path: str = "") -> TestStateInputTypeDefSlim:

        mock_mapping = orchestrator.mock_mapping
        items = self.get_items(input_data)
        response = orchestrator.client.test_state(
            definition=json.dumps(state_def),
            roleArn=orchestrator.role_arn,
            inspectionLevel="TRACE",
            variables=json.dumps(orchestrator.variables),
            input=json.dumps(input_data),
            mock={
                "result":json.dumps(items)
            }
        )

        items_ = json.loads(response["inspectionData"]["afterItemSelector"])
        new_parent_path = f"{parent_path}/{state_name}" if parent_path else state_name
        resp = [orchestrator.run_sub_machine(state_def["ItemProcessor"], item, mock_mapping=mock_mapping, parent_path=new_parent_path) for item
                in items_]
        return {"mock": {"result": json.dumps(resp)}, "context": context}


# --- 4. Implementation: Standard Flow Strategy ---
class StandardFlowStrategy(StateExecutionStrategy):
    """Handles Map, Parallel, and Nested SMs via recursion."""

    def execute(self, state_name, state_def, input_data, orchestrator, context=None, mock_mapping=None, parent_path=""):
        state_type = state_def.get("Type")
        resource = state_def.get("Resource", "")

        if "states:startExecution" in resource:
            result = {
                "OutputDetails": {
                    "Included": False
                },
                "Input": json.dumps(input_data),
                "ExecutionArn": "arn:aws:states:us-east-1:000000000000:execution:H5ad2Prod:GSE15471_affy_1769015448_1769015654669",
                "RedriveCount": 0,
                "InputDetails": {
                    "Included": False
                },
                "RedriveStatus": "NOT_REDRIVABLE",
                "RedriveStatusReason": "Execution is SUCCEEDED and cannot be redriven",
                "StartDate": "1769015654832",
                "StateMachineArn": "arn:aws:states:us-east-1:000000000000:stateMachine:H5ad2Prod",
                "Status": "SUCCEEDED",
                "StopDate": "1769015943200"
            }
            response = orchestrator.client.test_state(
                definition=json.dumps(state_def),
                roleArn=orchestrator.role_arn,
                inspectionLevel="TRACE",
                variables=json.dumps(orchestrator.variables),
                input=json.dumps(input_data),
                mock={
                    "result": json.dumps(result)
                }
            )
            if response.get('status') == 'FAILED':
                raise RuntimeError(f"State {state_name} failed: {response.get('error')}\n{response.get('cause')}")

            input_data_to_machine = json.loads(response["inspectionData"]["afterArguments"])["Input"]
            new_parent_path = f"{parent_path}/{state_name}" if parent_path else state_name
            resp = orchestrator.run_sub_machine(orchestrator.get_asl(state_name), input_data_to_machine, mock_mapping=mock_mapping, parent_path=new_parent_path)
            result["Output"] = json.dumps(resp)
            return {"mock": {"result": result["Output"], "fieldValidationMode":"PRESENT"}, "context": context}

        if state_type == "Parallel":
            new_parent_path = f"{parent_path}/{state_name}" if parent_path else state_name
            resp = [orchestrator.run_sub_machine(b, input_data, mock_mapping=mock_mapping, parent_path=new_parent_path) for b in
                    state_def.get("Branches", [])]
            return {"mock": {"result": json.dumps(resp)}, "context": context}

        if state_type == "Map":
            items = input_data if isinstance(input_data, list) else input_data.get("items", [])
            resp = [orchestrator.run_sub_machine(state_def["ItemProcessor"], item, mock_mapping=mock_mapping) for item
                    in items]
            return {"mock": {"result": json.dumps(resp)}, "context": context}

        return {}  # Fallback to default test_state behavior
