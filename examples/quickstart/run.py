"""Quickstart: run a small Step Functions state machine locally.

Copy this folder, then run:  python run.py

The ONLY thing you must edit is ROLE_ARN below — an IAM role allowed to call the
Step Functions TestState API. You also need AWS credentials + a region in your
environment (env vars, ~/.aws, SSO, etc.). No Docker required: this example mocks
its task steps, so it runs anywhere.
"""
import json
from pathlib import Path

from aws_stepfunctions_toolkit import (
    WorkflowRunner,
    StaticMockResponseStrategy,
    CallableStrategy,
)

# >>> **EDIT THIS** <<<
ROLE_ARN = "arn:aws:iam::<account>:role/<role-with-test-state-perms>"

HERE = Path(__file__).parent
definition = json.loads((HERE / "state_machine.asl.json").read_text())

mock_mapping = {
    # Your own function — gets the step's input, returns its (mocked) result:
    "Enrich": CallableStrategy(lambda data: {"Payload": {"enriched": True}}),
    # A fixed payload:
    "Notify": StaticMockResponseStrategy(json.dumps({"Payload": {"status": "sent"}})),
}

# Build the runner. "main" is the required entry-point key in asl_registry.
runner = WorkflowRunner(
    role_arn=ROLE_ARN,
    asl_registry={"main": definition},
    mock_mapping=mock_mapping,
)

final_output = runner.start(initial_input={"order_id": 123})
print(json.dumps(final_output, indent=2))
