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

# 1. EDIT THIS — an IAM role ARN allowed to call states:TestState.
ROLE_ARN = "arn:aws:iam::<account>:role/<role-with-test-state-perms>"

# 2. Load the state machine definition that ships next to this script.
HERE = Path(__file__).parent
definition = json.loads((HERE / "state_machine.asl.json").read_text())

# 3. Choose how each task step runs. (The "Prepare" Pass state needs nothing —
#    test_state handles it. We only map the two task steps.)
mock_mapping = {
    # Your own function — gets the step's input, returns its (mocked) result:
    "Enrich": CallableStrategy(lambda data: {"Payload": {"enriched": True}}),
    # A fixed payload:
    "Notify": StaticMockResponseStrategy(json.dumps({"Payload": {"status": "sent"}})),
}

# 4. Build the runner. "main" is the required entry-point key in asl_registry.
runner = WorkflowRunner(
    role_arn=ROLE_ARN,
    asl_registry={"main": definition},
    mock_mapping=mock_mapping,
)

# 5. Run the whole machine locally and print the final output.
final_output = runner.start(initial_input={"order_id": 123})
print(json.dumps(final_output, indent=2))
