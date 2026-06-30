"""Docker batch example: build a step's container from a Dockerfile and run it locally.

Set ROLE_ARN, then: uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py
Requires Docker running. AWS setup: ../../docs/setup.md

The basic version — the nested `child_flow` step is mocked with a StaticMockResponseStrategy.
See run_with_overrides.py to run the child machine for real with per-step hierarchical overrides.
"""
import json
import os
import tempfile
from pathlib import Path

from aws_stepfunctions_toolkit import (
    WorkflowRunner,
    DockerBatchStrategy,
    DockerfileImage,
    BakeImage,  # noqa: F401  (used in the commented bake alternative below)
    StaticMockResponseStrategy,
    CallableStrategy,
)

# >>> **EDIT THIS** <<< (or set the ROLE_ARN env var)
ROLE_ARN = os.environ.get("ROLE_ARN", "arn:aws:iam::<account>:role/<role-with-test-state-perms>")

HERE = Path(__file__).parent
PROJECT_FILE_DIR = HERE / "project_file"
definition = json.loads((HERE / "asl_definitions" / "main.asl.json").read_text())

workfolder = "/data"
variables = {"workfolder": workfolder}
volumes = [(tempfile.mkdtemp(), workfolder)]

mock_mapping = {
    # Build this Batch step's container from a plain Dockerfile and run it locally:
    "example_batch_1": DockerBatchStrategy(
        s3_bucket="placeholder",
        image_source=DockerfileImage(context=str(PROJECT_FILE_DIR / "example_batch_1")),
        # To build via `docker buildx bake` instead, swap the image source:
        #   image_source=BakeImage(bake_file=str(HERE / "docker-bake.hcl"),
        #                          target="example_batch_1", base_dir=str(HERE)),
        volumes=volumes,
        variables=variables,
    ),
    # Your own function (no container):
    "example_batch_2": CallableStrategy(lambda input_data: {"result": "result"}),
    # A fixed Lambda payload:
    "example_lambda_1": StaticMockResponseStrategy(json.dumps({"result": "result"})),
    # The nested-machine step (startExecution.sync:2) — mock its whole wrapper:
    "child_flow": StaticMockResponseStrategy(json.dumps({
        "ExecutionArn": "ExecutionArn",
        "StartDate": "1234567890",
        "StateMachineArn": "StateMachineArn",
        "Status": "SUCCEEDED",
    })),
}

runner = WorkflowRunner(
    role_arn=ROLE_ARN,
    asl_registry={"main": definition},
    variables=variables,
    mock_mapping=mock_mapping,
)

runner_input = {
    "mem": {"example_batch_1": 12, "example_batch_2": 12},
    "cpu": {"example_batch_1": 4, "example_batch_2": 4},
    "data": "somedata",
}

print(json.dumps(runner.start(runner_input), indent=2))
