"""Docker Lambda example: run a real Lambda container image locally via the RIE.

Set ROLE_ARN, then: uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py
Requires Docker running. AWS setup: ../../docs/setup.md

DockerLambdaStrategy builds the Lambda's image (here from a plain Dockerfile), runs it via
the AWS Runtime Interface Emulator, POSTs the resolved lambda:invoke Payload, and feeds the
real handler output downstream. The ASL keeps its real `$states.result.Payload` expression —
the runner rewrites it to `$parse(...)` because the mocked result's Payload is a JSON string.
"""

import json
import os
from pathlib import Path

from aws_stepfunctions_toolkit import (
    WorkflowRunner,
    DockerLambdaStrategy,
    DockerfileImage,
)

# >>> **EDIT THIS** <<< (or set the ROLE_ARN env var)
ROLE_ARN = os.environ.get(
    "ROLE_ARN", "arn:aws:iam::<account>:role/<role-with-test-state-perms>"
)

HERE = Path(__file__).parent
definition = json.loads((HERE / "asl_definitions" / "main.asl.json").read_text())

mock_mapping = {
    # Build the Lambda's container image and invoke the real handler via the RIE:
    "double_it": DockerLambdaStrategy(
        image_source=DockerfileImage(
            context=str(HERE / "project_file" / "echo_lambda")
        ),
    ),
}

runner = WorkflowRunner(
    asl_registry={"main": {**definition, "ROLE_ARN": ROLE_ARN}},
    mock_mapping=mock_mapping,
)

# The handler doubles `number` and echoes the event; expect {"doubled": 42, "echo": {...}}.
print(json.dumps(runner.start(initial_input={"number": 21}), indent=2))
