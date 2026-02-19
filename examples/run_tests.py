import os
import logging
import json
from pathlib import Path

import pytest
from aws_stepfunctions_toolkit.workflow_runner.strategies import LocalBatchImageStrategy, StaticMockResponseStrategy
from aws_stepfunctions_toolkit.workflow_runner.workflow_runner import WorkflowRunner

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

THIS_DIR = Path(__file__).parent
DEFINITIONS_DIR = THIS_DIR.joinpath("asl_definitions")


@pytest.fixture
def definitions() -> dict[str, dict]:
    return {
        "main": json.loads((DEFINITIONS_DIR / "main.asl.json").read_text()),
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
    logger.debug(f"{definitions.keys()=}")
    workfolder = "/data"
    variables = {"workfolder": workfolder}

    volumes = [
        (str(tmp_path), workfolder),
    ]

    bake_file = THIS_DIR.joinpath("docker-bake.hcl")

    strategy_mapping = {
        "example_batch_1": LocalBatchImageStrategy(
            "placeholder",
            "example_batch_1",
            bake_file,
            volumes=volumes,
            variables=variables,
            base_dir=str(THIS_DIR)
        ),
        "example_batch_2": StaticMockResponseStrategy(
            json.dumps(
                {
                    "JobDefinitions": [{
                        "JobDefinitionArn": "arn:aws:batch:us-east-1:${accountId}:job-definition/example_batch_1:1",
                        "JobDefinitionName": "example_batch_1",
                        "Revision": 1,
                        "Type": "container"
                    }]
                }
            )
        ),
        "child_flow": StaticMockResponseStrategy(
            json.dumps(
                {"datasetLocation": "/tmp"}
            )
        )
    }

    role_arn = os.environ.get("ROLE_ARN")
    runner = WorkflowRunner(
        role_arn=role_arn,
        asl_registry={
            "main": definitions["main"],
            "child-flow": definitions["child"]
        },
        variables=variables,
        mock_mapping=strategy_mapping
    )

    runner.start(runner_input, strategy_mapping)
