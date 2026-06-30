"""Docker batch example — per-SFN step overrides (hierarchical keys).

Same pipeline as run.py, but it registers the nested `child_flow` machine and runs it for
real. The child reuses the parent's step names, so hierarchical "child_flow/<step>" keys
override just the child's occurrences (the parent's example_batch_1 still builds a real
container).

Set ROLE_ARN, then: uv run --python=3.13 --with aws-stepfunctions-toolkit python run_with_overrides.py
Requires Docker running. AWS setup: ../../docs/setup.md
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
ROLE_ARN = os.environ.get(
    "ROLE_ARN", "arn:aws:iam::<account>:role/<role-with-test-state-perms>"
)

HERE = Path(__file__).parent
PROJECT_FILE_DIR = HERE / "project_file"
DEFINITIONS_DIR = HERE / "asl_definitions"
main_definition = json.loads((DEFINITIONS_DIR / "main.asl.json").read_text())
child_definition = json.loads((DEFINITIONS_DIR / "child.asl.json").read_text())

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

# The "main" machine and the nested "child_flow" machine share the same step names
# (example_batch_1/2, example_lambda_1). A flat key matches a step anywhere; a
# hierarchical "<parent-state>/<step>" key overrides just that occurrence — so the
# parent's example_batch_1 builds a real container while the child's steps are mocked.
mock_mapping = {
    # --- "main" steps ---
    # Build this Batch step's container and run it locally:
    "example_batch_1": DockerBatchStrategy(
        s3_bucket="placeholder",
        image_source=image_source,
        volumes=volumes,
        variables=variables,
    ),
    "example_batch_2": CallableStrategy(
        lambda input_data: {"result": "result"}
    ),  # your own function
    "example_lambda_1": StaticMockResponseStrategy(json.dumps({"result": "result"})),
    # --- per-SFN overrides: the child reuses the same names, so target it by path ---
    "child_flow/example_batch_1": StaticMockResponseStrategy(
        json.dumps({"result": "child-batch-1"})
    ),
    "child_flow/example_batch_2": StaticMockResponseStrategy(
        json.dumps({"result": "child-batch-2"})
    ),
    "child_flow/example_lambda_1": StaticMockResponseStrategy(
        json.dumps({"result": "child-lambda"})
    ),
}

# child_flow is a startExecution.sync:2 step; registering the child machine here lets the
# default StandardFlowStrategy recurse into it (rather than mocking the whole sub-run).
runner = WorkflowRunner(
    role_arn=ROLE_ARN,
    asl_registry={"main": main_definition, "child_flow": child_definition},
    variables=variables,
    mock_mapping=mock_mapping,
)

runner_input = {
    "mem": {"example_batch_1": 12, "example_batch_2": 12},
    "cpu": {"example_batch_1": 4, "example_batch_2": 4},
    "data": "somedata",
}

print(json.dumps(runner.start(runner_input), indent=2))
