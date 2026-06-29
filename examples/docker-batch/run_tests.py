import os
import logging
import json
from pathlib import Path

import pytest
from aws_stepfunctions_toolkit import (
    WorkflowRunner,
    DockerBatchStrategy,
    DockerfileImage,
    BakeImage,
    StaticMockResponseStrategy,
    CallableStrategy,
)

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

THIS_DIR = Path(__file__).parent
DEFINITIONS_DIR = THIS_DIR.joinpath("asl_definitions")
PROJECT_FILE_DIR = THIS_DIR.joinpath("project_file")


@pytest.fixture
def definitions() -> dict[str, dict]:
    return {
        "parent": json.loads((DEFINITIONS_DIR / "main.asl.json").read_text()),
        "child": json.loads((DEFINITIONS_DIR / "child.asl.json").read_text())
    }


@pytest.fixture
def runner_input() -> dict:
    return {
        "mem": {"example_batch_1": 12, "example_batch_2": 12},
        "cpu": {"example_batch_1": 4, "example_batch_2": 4},
        "data": "somedata"
    }


def test_example_1(
        runner_input, definitions: dict[str, dict], tmp_path: Path
):
    """The easy path: build the batch container from a plain Dockerfile (no bake file)."""
    logger.debug(f"{definitions.keys()=}")
    workfolder = "/data"
    variables = {"workfolder": workfolder}

    volumes = [
        (str(tmp_path), workfolder),
    ]

    strategy_mapping = {
        "example_lambda_1": StaticMockResponseStrategy(
            json.dumps({"result": "result"})
        ),
        "example_batch_1": DockerBatchStrategy(
            s3_bucket="placeholder",
            image_source=DockerfileImage(context=str(PROJECT_FILE_DIR / "example_batch_1")),
            volumes=volumes,
            variables=variables,
        ),
        # Define your own handler inline with a plain function — no subclassing.
        "example_batch_2": CallableStrategy(lambda input_data: {"result": "result"}),
        "child_flow": StaticMockResponseStrategy(
            json.dumps({
                "ExecutionArn": "ExecutionArn",
                "StartDate": "1234567890",
                "StateMachineArn": "StateMachineArn",
                "Status": "SUCCEEDED"
            })
        )
    }

    role_arn = os.environ.get("ROLE_ARN")
    runner = WorkflowRunner(
        role_arn=role_arn,
        asl_registry={
            "main": definitions["parent"]
        },
        variables=variables,
        mock_mapping=strategy_mapping
    )

    runner.start(runner_input)


def test_example_2(
        runner_input, definitions: dict[str, dict], tmp_path: Path
):
    """The advanced path: build the same container via docker buildx bake."""
    logger.debug(f"{definitions.keys()=}")
    workfolder = "/data"
    variables = {"workfolder": workfolder}

    volumes = [
        (str(tmp_path), workfolder),
    ]

    bake_file = THIS_DIR.joinpath("docker-bake.hcl")

    strategy_mapping = {
        "example_lambda_1": StaticMockResponseStrategy(
            json.dumps({"result": "result"})
        ),
        "example_batch_1": DockerBatchStrategy(
            s3_bucket="placeholder",
            image_source=BakeImage(
                bake_file=str(bake_file),
                target="example_batch_1",
                base_dir=str(THIS_DIR),
            ),
            volumes=volumes,
            variables=variables,
        ),
        "example_batch_2": StaticMockResponseStrategy(
            json.dumps({"result": "result"})
        ),
        "child_flow/example_batch_2": StaticMockResponseStrategy(
            json.dumps({"result": "result"})
        )
    }

    role_arn = os.environ.get("ROLE_ARN")
    runner = WorkflowRunner(
        role_arn=role_arn,
        asl_registry={
            "main": definitions["parent"],
            "child_flow": definitions["child"]
        },
        variables=variables,
        mock_mapping=strategy_mapping
    )

    runner.start(runner_input)
