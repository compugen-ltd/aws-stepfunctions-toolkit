from __future__ import annotations

import os
import logging
import json
import socket
import time
import uuid
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, TYPE_CHECKING

import boto3
from python_on_whales import docker
from mypy_boto3_appconfigdata import AppConfigDataClient
from mypy_boto3_batch.client import BatchClient
from mypy_boto3_batch.type_defs import ContainerOverridesTypeDef, KeyValuePairTypeDef
from mypy_boto3_s3.client import S3Client

if TYPE_CHECKING:
    from .workflow_runner import WorkflowRunner

from ._common import TestStateInputTypeDefSlim, resolve_region
from .image_sources import (
    ImageSource,
    BakeImage,
    login_to_ecr,  # noqa: F401  (re-exported)
    get_codeartifact_token,  # noqa: F401  (re-exported)
)
from .models import DockerBatchConfig, StartExecutionResult

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def get_container_overrides(
    sfn_client,
    state_def: dict,
    role_arn: str,
    variables: dict,
    input_data: dict,
    context: str | None,
) -> dict:
    """Use the test API to resolve a Batch task's ContainerOverrides (Command + Environment).

    Runs ``test_state`` in TRACE mode with an empty mock so AWS evaluates the
    state's Arguments/Parameters, then returns the resolved ``ContainerOverrides``.
    """
    response = sfn_client.test_state(
        definition=json.dumps(state_def),
        roleArn=role_arn,
        variables=json.dumps(variables),
        input=json.dumps(input_data),
        inspectionLevel="TRACE",
        context=context,
        mock={"result": json.dumps({}), "fieldValidationMode": "PRESENT"},
    )
    inspection = response.get("inspectionData", {})
    after_args = inspection.get("afterArguments")
    if not after_args:
        raise RuntimeError(
            f"test_state did not return afterArguments. "
            f"inspectionData keys: {list(inspection.keys())}"
        )
    return json.loads(after_args)["ContainerOverrides"]


def get_lambda_payload(
    sfn_client,
    state_def: dict,
    role_arn: str,
    variables: dict,
    input_data: dict,
    context: str | None,
) -> dict:
    """Use the test API to resolve a ``lambda:invoke`` state's ``Payload`` (the event).

    Runs ``test_state`` in TRACE mode with an empty mock so AWS evaluates the state's
    Arguments, then returns the resolved ``Payload`` — exactly the event Step Functions
    would pass to the Lambda handler.
    """
    response = sfn_client.test_state(
        definition=json.dumps(state_def),
        roleArn=role_arn,
        variables=json.dumps(variables),
        input=json.dumps(input_data),
        inspectionLevel="TRACE",
        context=context,
        mock={"result": json.dumps({}), "fieldValidationMode": "PRESENT"},
    )
    inspection = response.get("inspectionData", {})
    after_args = inspection.get("afterArguments")
    if not after_args:
        raise RuntimeError(
            f"test_state did not return afterArguments. "
            f"inspectionData keys: {list(inspection.keys())}"
        )
    arguments = json.loads(after_args)
    if "Payload" not in arguments:
        raise RuntimeError(
            f"lambda:invoke Arguments has no 'Payload' (got keys {list(arguments.keys())}). "
            f"A lambda:invoke state must set Arguments.Payload to the event to send."
        )
    return arguments["Payload"]


# --- 1. Execution Strategy Interface ---
class StateExecutionStrategy(ABC):
    @abstractmethod
    def execute(
        self,
        state_name: str,
        state_def: dict,
        input_data: dict,
        orchestrator: WorkflowRunner,
        context: str | None = None,
        parent_path: str = "",
    ) -> TestStateInputTypeDefSlim:
        pass


class DockerBatchStrategy(StateExecutionStrategy):
    """Runs a Batch (or any container) task locally via Docker.

    The image is produced by a pluggable ``ImageSource`` (``DockerfileImage`` for a plain
    Dockerfile build, ``PrebuiltImage`` for an existing/ECR image, ``BakeImage`` for
    ``docker buildx bake``, or your own). This strategy only resolves the container's
    Command/Environment from the state, runs the container, and reads its output.

    The container is expected to write its result JSON to ``/tmp/output.json`` (the toolkit
    mounts a writable temp dir at ``/tmp`` and injects ``OUTPUT_PATH``/``S3_OUTPUT_PATH``).
    """

    def __init__(
        self,
        s3_bucket: str,
        image_source: ImageSource,
        execution_id: str | None = None,
        volumes: list | None = None,
        variables: dict | None = None,
        user: str | None = None,
        gpus: str | None = None,
        extra_run_envs: dict | None = None,
        region: str | None = None,
        s3_client: S3Client | None = None,
    ):
        if not isinstance(image_source, ImageSource):
            raise TypeError(
                "image_source must be an ImageSource (e.g. DockerfileImage, PrebuiltImage, BakeImage)"
            )
        self.s3_bucket = s3_bucket
        self.image_source = image_source
        self.execution_id = execution_id or f"test-{uuid.uuid4().hex[:6]}"
        self.s3_client: S3Client = s3_client or boto3.client(
            "s3", region_name=resolve_region(region)
        )
        self.volumes = volumes
        self.variables = variables or dict()
        self.user = user
        self.gpus = gpus
        self.extra_run_envs = extra_run_envs

    def _run_image(self, run_image: str, command, s3_out: str, extra_envs: dict) -> str:
        tmpdir = tempfile.mkdtemp()
        try:
            os.chmod(tmpdir, 0o777)
            output_path = "/tmp/output.json"
            run_kwargs = {
                "image": run_image,
                "command": command,
                "envs": {"S3_OUTPUT_PATH": s3_out, "OUTPUT_PATH": output_path}
                | (self.extra_run_envs or {})
                | extra_envs,
                "remove": True,
                "user": self.user,
                "volumes": (self.volumes or []) + [(str(tmpdir), "/tmp", "rw")],
            }
            if self.gpus:
                run_kwargs["gpus"] = self.gpus
            docker.run(**run_kwargs)
            data = Path(tmpdir).joinpath("output.json").read_text()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        return data

    def execute(
        self,
        state_name,
        state_def,
        input_data,
        orchestrator,
        context=None,
        parent_path="",
    ):
        s3_out = f"s3://{self.s3_bucket}/{self.execution_id}/{state_name}/output.json"

        overrides = get_container_overrides(
            orchestrator.client,
            state_def,
            orchestrator.active_role_arn,
            self.variables,
            input_data,
            context,
        )
        command = overrides["Command"]
        envs = {ele["Name"]: ele["Value"] for ele in overrides["Environment"]}
        envs.pop("TaskToken", None)

        run_image = self.image_source.ensure_image()
        data = self._run_image(run_image, command, s3_out, envs)

        return {"mock": {"result": data}, "context": context}


BatchImageStrategy = DockerBatchStrategy
LocalBatchImageStrategy = DockerBatchStrategy


# --- 1a. Implementation: Local Lambda container image via the Runtime Interface Emulator ---
# AWS Lambda base images ship the Runtime Interface Emulator (RIE), which exposes this HTTP
# endpoint on container port 8080. POSTing the event runs the real handler locally.
RIE_CONTAINER_PORT: int = 8080
RIE_INVOCATION_PATH: str = "/2015-03-31/functions/function/invocations"


class DockerLambdaStrategy(StateExecutionStrategy):
    """Runs a real AWS Lambda **container image** locally via the Runtime Interface Emulator.

    This is the Lambda counterpart to ``DockerBatchStrategy``: instead of faking a
    ``lambda:invoke`` step with a hand-written mock, it runs the Lambda's real image and
    returns the handler's real output. The image is produced by a pluggable ``ImageSource``
    (``DockerfileImage`` / ``PrebuiltImage`` / ``BakeImage`` / your own).

    AWS Lambda base images (``public.ecr.aws/lambda/python:*`` etc.) include the Runtime
    Interface Emulator (RIE), which serves ``POST /2015-03-31/functions/function/invocations``.
    This strategy resolves the event ``Payload`` the state would pass (via the test API), runs
    the image detached with the RIE port published, ``POST``\\ s the event, then returns the
    handler response wrapped as the Step Functions ``lambda:invoke`` result shape
    (``{"Payload": <json-string>}``) so downstream ``$states.result.Payload`` expressions
    resolve (the runner rewrites that to ``$parse(...)`` for mocked lambda steps).

        DockerLambdaStrategy(image_source=DockerfileImage(context="jobs/my_lambda"))
    """

    DEFAULT_STARTUP_TIMEOUT: float = 30.0

    def __init__(
        self,
        image_source: ImageSource,
        variables: dict | None = None,
        extra_run_envs: dict | None = None,
        forward_aws_envs: bool = True,
        startup_timeout: float = DEFAULT_STARTUP_TIMEOUT,
        region: str | None = None,
    ):
        if not isinstance(image_source, ImageSource):
            raise TypeError(
                "image_source must be an ImageSource (e.g. DockerfileImage, PrebuiltImage, BakeImage)"
            )
        self.image_source = image_source
        self.variables = variables or dict()
        self.extra_run_envs = extra_run_envs or {}
        self.forward_aws_envs = forward_aws_envs
        self.startup_timeout = startup_timeout
        self.region = region

    def _aws_envs(self) -> dict:
        """AWS_* env forwarded into the container so the handler's AWS calls work."""
        if not self.forward_aws_envs:
            return {}
        envs = {k: v for k, v in os.environ.items() if k.startswith("AWS_")}
        region = resolve_region(self.region)
        if region:
            envs.setdefault("AWS_REGION", region)
            envs.setdefault("AWS_DEFAULT_REGION", region)
        return envs

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("", 0))
            return sock.getsockname()[1]

    def _post_event(self, url: str, payload: dict) -> dict:
        """POST the event to the RIE, retrying until the emulator is up or we time out."""
        data = json.dumps(payload).encode("utf-8")
        deadline = time.monotonic() + self.startup_timeout
        last_err: Exception | None = None
        while time.monotonic() < deadline:
            try:
                request = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(
                    request, timeout=self.startup_timeout
                ) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except (urllib.error.URLError, ConnectionError, OSError) as e:
                last_err = e
                time.sleep(0.5)
        raise RuntimeError(
            f"Lambda RIE at {url} did not respond within {self.startup_timeout}s: {last_err}"
        )

    def _invoke_via_rie(self, run_image: str, payload: dict, extra_envs: dict) -> dict:
        host_port = self._free_port()
        envs = self._aws_envs() | self.extra_run_envs | extra_envs
        envs.pop("TaskToken", None)
        container = docker.run(
            run_image,
            detach=True,
            remove=True,
            publish=[(host_port, RIE_CONTAINER_PORT)],
            envs=envs,
        )
        try:
            url = f"http://localhost:{host_port}{RIE_INVOCATION_PATH}"
            return self._post_event(url, payload)
        finally:
            try:
                docker.stop(container)
            except Exception:  # container may already be gone (--rm)
                logger.debug(
                    "failed to stop RIE container (already removed?)", exc_info=True
                )

    def execute(
        self,
        state_name,
        state_def,
        input_data,
        orchestrator,
        context=None,
        parent_path="",
    ):
        payload = get_lambda_payload(
            orchestrator.client,
            state_def,
            orchestrator.active_role_arn,
            self.variables,
            input_data,
            context,
        )
        run_image = self.image_source.ensure_image()
        response = self._invoke_via_rie(run_image, payload, {})
        # Wrap as the lambda:invoke result shape. Payload is a JSON *string* (test_state
        # requires it); alter_mock_step rewrites the state's $states.result.Payload to
        # $parse($states.result.Payload) so downstream reads get the handler's object back.
        result = {
            "ExecutedVersion": "$LATEST",
            "Payload": json.dumps(response),
            "StatusCode": 200,
        }
        return {"mock": {"result": json.dumps(result)}, "context": context}


LocalLambdaImageStrategy = DockerLambdaStrategy


# --- 1b. Implementation: Local subprocess (no Docker) ---
class LocalExecutionStrategy(StateExecutionStrategy):
    """Run a step locally as a subprocess — directly in your terminal, no Docker.

    This is the no-Docker counterpart to ``DockerBatchStrategy``: it resolves the step's
    ``Command`` + ``Environment`` from the ASL (via the test API), prepends ``entrypoint``
    (the program to run — the local equivalent of a container's ENTRYPOINT), injects
    ``OUTPUT_PATH`` (a temp file) and ``S3_OUTPUT_PATH``, removes ``TaskToken``, runs the
    process, and reads the result JSON the process writes to ``OUTPUT_PATH``.

    The same job code (e.g. one using ``BatchJobInterface``) runs unchanged here or in a
    container, since both honor the ``OUTPUT_PATH`` contract.

        LocalExecutionStrategy(entrypoint=["python", "jobs/process_data/main.py"])
    """

    def __init__(
        self,
        entrypoint: list[str] | None = None,
        s3_bucket: str | None = None,
        execution_id: str | None = None,
        cwd: str | None = None,
        extra_env: dict | None = None,
        inherit_env: bool = True,
        variables: dict | None = None,
    ):
        self.entrypoint = list(entrypoint) if entrypoint else []
        self.s3_bucket = s3_bucket
        self.execution_id = execution_id or f"test-{uuid.uuid4().hex[:6]}"
        self.cwd = cwd
        self.extra_env = extra_env or {}
        self.inherit_env = inherit_env
        self.variables = variables or dict()

    def _run_local(self, command, extra_envs: dict, state_name: str) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.json"
            s3_out = (
                f"s3://{self.s3_bucket}/{self.execution_id}/{state_name}/output.json"
                if self.s3_bucket
                else ""
            )
            env = dict(os.environ) if self.inherit_env else {}
            env.update(extra_envs)
            env.update(self.extra_env)
            env["OUTPUT_PATH"] = str(output_path)
            env["S3_OUTPUT_PATH"] = s3_out

            full_cmd = [*self.entrypoint, *command]
            logger.info(f"Running locally: {full_cmd}")
            subprocess.run(full_cmd, env=env, cwd=self.cwd, check=True)

            if not output_path.exists():
                raise RuntimeError(
                    f"Local process for '{state_name}' did not write OUTPUT_PATH ({output_path}). "
                    f"The command must write its result JSON to the file named by $OUTPUT_PATH."
                )
            return output_path.read_text()

    def execute(
        self,
        state_name,
        state_def,
        input_data,
        orchestrator,
        context=None,
        parent_path="",
    ):
        overrides = get_container_overrides(
            orchestrator.client,
            state_def,
            orchestrator.active_role_arn,
            self.variables,
            input_data,
            context,
        )
        command = overrides["Command"]
        envs = {ele["Name"]: ele["Value"] for ele in overrides["Environment"]}
        envs.pop("TaskToken", None)
        data = self._run_local(command, envs, state_name)
        return {"mock": {"result": data}, "context": context}


# --- 2. Implementation: Callable (user-defined) Strategy ---
class CallableStrategy(StateExecutionStrategy):
    """Wrap a plain function as a strategy — the simplest way to define your own handler.

    ``handler`` receives the state's input dict and returns the state's result either as a
    dict/list (json-encoded for you) or as a pre-serialized JSON string.

        CallableStrategy(lambda input_data: {"ok": True, "echo": input_data})
    """

    def __init__(self, handler: Callable[[dict], dict | list | str]):
        self.handler = handler

    def execute(
        self,
        state_name,
        state_def,
        input_data,
        orchestrator,
        context=None,
        parent_path="",
    ):
        result = self.handler(input_data)
        if not isinstance(result, str):
            result = json.dumps(result)
        return {"mock": {"result": result}, "context": context}


# --- 3. Implementation: AppConfig Strategy ---
class GetLatestConfigurationStrategy(StateExecutionStrategy):
    """Resolves a state's result from AWS AppConfig (start session + get latest configuration)."""

    def __init__(
        self,
        application: str,
        environment: str,
        configuration_profile: str,
        appconfigdata_client: AppConfigDataClient | None = None,
        region: str | None = None,
    ):
        self.application = application
        self.environment = environment
        self.configuration_profile = configuration_profile
        if not appconfigdata_client:
            appconfigdata_client = boto3.client(
                "appconfigdata", region_name=resolve_region(region)
            )
        self.appconfigdata_client = appconfigdata_client

    def execute(
        self,
        state_name,
        state_def,
        input_data,
        orchestrator,
        context: str = "{}",
        parent_path="",
    ):
        appconfigdata_client = self.appconfigdata_client
        response = appconfigdata_client.start_configuration_session(
            ApplicationIdentifier=self.application,
            EnvironmentIdentifier=self.environment,
            ConfigurationProfileIdentifier=self.configuration_profile,
        )

        response = appconfigdata_client.get_latest_configuration(
            ConfigurationToken=response["InitialConfigurationToken"],
        )

        data = response["Configuration"].read().decode("utf8")
        return {"mock": {"result": data}, "context": context}


# --- 4. Implementation: Static Mock Strategy ---
class StaticMockResponseStrategy(StateExecutionStrategy):
    """Returns a fixed, caller-supplied JSON string as the state's result."""

    def __init__(self, result: str):
        self.result = result

    def execute(
        self,
        state_name,
        state_def,
        input_data,
        orchestrator,
        context=None,
        parent_path="",
    ):
        return {"mock": {"result": self.result}, "context": context}


# --- 5. Implementation: Batch Job Submission Strategy ---
class BatchJobResponseStrategy(StateExecutionStrategy):
    """Submits a real AWS Batch job (rather than running the container locally)."""

    def __init__(
        self,
        job_queue: str,
        job_definition: str,
        job_name: str | None = None,
        batch_client: BatchClient | None = None,
        variables: dict | None = None,
        region: str | None = None,
    ):
        if not batch_client:
            batch_client = boto3.client("batch", region_name=resolve_region(region))
        self.client = batch_client
        self.job_queue = job_queue
        self.job_name = job_name or "sometestjob"
        self.job_definition = job_definition
        self.variables = variables or {}

    def execute(
        self,
        state_name,
        state_def,
        input_data,
        orchestrator,
        context=None,
        parent_path="",
    ):
        container_overrides = get_container_overrides(
            orchestrator.client,
            state_def,
            orchestrator.active_role_arn,
            self.variables,
            input_data,
            context,
        )
        environment = [
            KeyValuePairTypeDef(name=env["Name"], value=env["Value"])
            for env in container_overrides["Environment"]
        ]

        _ = self.client.submit_job(
            jobName=self.job_name,
            jobQueue=self.job_queue,
            jobDefinition=self.job_definition,
            containerOverrides=ContainerOverridesTypeDef(
                environment=environment, command=container_overrides["Command"]
            ),
        )

        # TODO: get results from s3
        return {}


# --- 6. Implementation: Map Response Strategy ---
class AbstractMockMapResponseStrategy(StateExecutionStrategy, ABC):
    """Base for Map states: implement ``get_items`` to supply the items to iterate.

    Each item is run through the Map's ItemProcessor via ``run_sub_machine``.
    """

    @abstractmethod
    def get_items(self, input_data):
        pass

    def execute(
        self,
        state_name: str,
        state_def: dict,
        input_data: dict,
        orchestrator: WorkflowRunner,
        context: str | None = None,
        parent_path: str = "",
    ) -> TestStateInputTypeDefSlim:
        mock_mapping = orchestrator.mock_mapping
        items = self.get_items(input_data)
        response = orchestrator.client.test_state(
            definition=json.dumps(state_def),
            roleArn=orchestrator.active_role_arn,
            inspectionLevel="TRACE",
            variables=json.dumps(orchestrator.variables),
            input=json.dumps(input_data),
            mock={"result": json.dumps(items)},
        )
        if response.get("inspectionData", {}).get("afterItemSelector") is None:
            raise RuntimeError(
                f"Expected afterItemSelector in inspectionData but got: {response.get('inspectionData')}"
            )

        items_ = json.loads(
            response.get("inspectionData", {}).get("afterItemSelector", "[]")
        )
        new_parent_path = f"{parent_path}/{state_name}" if parent_path else state_name
        resp = [
            orchestrator.run_sub_machine(
                state_def["ItemProcessor"],
                item,
                mock_mapping=mock_mapping,
                parent_path=new_parent_path,
            )
            for item in items_
        ]
        return {"mock": {"result": json.dumps(resp)}, "context": context}


# --- 7. Implementation: Standard Flow Strategy ---
class StandardFlowStrategy(StateExecutionStrategy):
    """Handles Map, Parallel, and Nested SMs via recursion."""

    def execute(
        self,
        state_name,
        state_def,
        input_data,
        orchestrator,
        context=None,
        mock_mapping=None,
        parent_path="",
    ):
        state_type = state_def.get("Type")
        resource = state_def.get("Resource", "")

        if "states:startExecution" in resource:
            # startExecution.sync:2 returns a wrapper with Output, Status, ExecutionArn, etc.
            # We mock this wrapper to extract the transformed input via afterArguments,
            # then recursively run the nested state machine and inject its output back.
            result = StartExecutionResult(Input=json.dumps(input_data)).model_dump()
            response = orchestrator.client.test_state(
                definition=json.dumps(state_def),
                roleArn=orchestrator.active_role_arn,
                inspectionLevel="TRACE",
                variables=json.dumps(orchestrator.variables),
                input=json.dumps(input_data),
                mock={"result": json.dumps(result)},
            )
            if response.get("status") == "FAILED":
                raise RuntimeError(
                    f"State {state_name} failed: {response.get('error')}\n{response.get('cause')}"
                )

            input_data_to_machine = json.loads(
                response["inspectionData"]["afterArguments"]
            )["Input"]
            new_parent_path = (
                f"{parent_path}/{state_name}" if parent_path else state_name
            )
            sub_asl = orchestrator.get_asl(state_name)
            if sub_asl is None:
                raise RuntimeError(
                    f"Sub-machine '{state_name}' not found in ASL registry. "
                    f"Available: {list(orchestrator.asl_registry.keys())}. "
                    f"Add it to the asl_registry when constructing WorkflowRunner."
                )
            # Cross an SM boundary: the sub-machine runs under its own execution role.
            # Switch the active role for the recursion, then restore the parent's role.
            previous_role = orchestrator.active_role_arn
            orchestrator.active_role_arn = orchestrator.role_for(sub_asl)
            try:
                resp = orchestrator.run_sub_machine(
                    sub_asl,
                    input_data_to_machine,
                    mock_mapping=mock_mapping,
                    parent_path=new_parent_path,
                )
            finally:
                orchestrator.active_role_arn = previous_role
            result["Output"] = json.dumps(resp)
            # Return the full startExecution wrapper (with Output as a JSON string) so the
            # parent state's `$states.result.Output` reads the child's output.
            return {
                "mock": {
                    "result": json.dumps(result),
                    "fieldValidationMode": "PRESENT",
                },
                "context": context,
            }

        if state_type == "Parallel":
            new_parent_path = (
                f"{parent_path}/{state_name}" if parent_path else state_name
            )
            resp = [
                orchestrator.run_sub_machine(
                    b,
                    input_data,
                    mock_mapping=mock_mapping,
                    parent_path=new_parent_path,
                )
                for b in state_def.get("Branches", [])
            ]
            return {"mock": {"result": json.dumps(resp)}, "context": context}

        if state_type == "Map":
            items = (
                input_data
                if isinstance(input_data, list)
                else input_data.get("items", [])
            )
            resp = [
                orchestrator.run_sub_machine(
                    state_def["ItemProcessor"], item, mock_mapping=mock_mapping
                )
                for item in items
            ]
            return {"mock": {"result": json.dumps(resp)}, "context": context}

        return {}


# --- 8. Helper: Build strategy mappings from DockerBatchConfig (bake convenience) ---
def build_strategies(config: DockerBatchConfig) -> dict[str, DockerBatchStrategy]:
    return {
        state_name: DockerBatchStrategy(
            s3_bucket=config.s3_bucket,
            image_source=BakeImage(bake_file=config.bake_file, target=target_name),
            volumes=config.volumes,
            variables=config.variables,
            user=config.user,
        )
        for state_name, target_name in config.target_mapping.items()
    }
