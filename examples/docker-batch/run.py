"""Docker batch example: build a step's container and run it locally.

Set ROLE_ARN, then: uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py
Requires Docker running. AWS setup: ../../docs/setup.md

The batch container is built from a plain Dockerfile by default; set IMAGE_SOURCE=bake to
build it via `docker buildx bake` instead. The nested `child_flow` step is mocked with a
StaticMockResponseStrategy — see run_with_overrides.py to run the child machine for real.
"""

import json
import os
import tempfile
from pathlib import Path

from aws_stepfunctions_toolkit import (
    WorkflowRunner,
    DockerBatchStrategy,
    DockerfileImage,
    BakeImage,
    StaticMockResponseStrategy,
    CallableStrategy,
)

# >>> **EDIT THIS** <<< (or set the ROLE_ARN env var)
ROLE_ARN = os.environ.get(
    "ROLE_ARN", "arn:aws:iam::<account>:role/<role-with-test-state-perms>"
)

HERE = Path(__file__).parent
PROJECT_FILE_DIR = HERE / "project_file"
definition = json.loads((HERE / "asl_definitions" / "main.asl.json").read_text())

workfolder = "/data"
variables = {"workfolder": workfolder}
volumes = [(tempfile.mkdtemp(), workfolder)]

# How to build the example_batch_1 image: a plain Dockerfile (default) or docker buildx bake.
if os.environ.get("IMAGE_SOURCE") == "bake":
    image_source = BakeImage(
        bake_file=str(HERE / "docker-bake.hcl"),
        target="example_batch_1",
        base_dir=str(HERE),
    )
else:
    image_source = DockerfileImage(context=str(PROJECT_FILE_DIR / "example_batch_1"))

mock_mapping = {
    # Build this Batch step's container and run it locally:
    "example_batch_1": DockerBatchStrategy(
        s3_bucket="placeholder",
        image_source=image_source,
        volumes=volumes,
        variables=variables,
    ),
    # Your own function (no container):
    "example_batch_2": CallableStrategy(lambda input_data: {"result": "result"}),
    # A fixed Lambda payload:
    "example_lambda_1": StaticMockResponseStrategy(json.dumps({"result": "result"})),
    # The nested-machine step (startExecution.sync:2) — mock its whole wrapper:
    "child_flow": StaticMockResponseStrategy(
        json.dumps(
            {
                "ExecutionArn": "ExecutionArn",
                "StartDate": "1234567890",
                "StateMachineArn": "StateMachineArn",
                "Status": "SUCCEEDED",
            }
        )
    ),
}

runner = WorkflowRunner(
    # Each state machine carries its own execution role (the role its states run under).
    asl_registry={"main": {**definition, "ROLE_ARN": ROLE_ARN}},
    variables=variables,
    mock_mapping=mock_mapping,
)

runner_input = {
    "mem": {"example_batch_1": 12, "example_batch_2": 12},
    "cpu": {"example_batch_1": 4, "example_batch_2": 4},
    "data": "somedata",
}

print(json.dumps(runner.start(runner_input), indent=2))
