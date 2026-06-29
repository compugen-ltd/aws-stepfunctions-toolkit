"""Quickstart: run a small Step Functions state machine locally.

Set ROLE_ARN, then: uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py
No Docker — the task steps are mocked. AWS setup: ../../docs/setup.md
"""
import json
from pathlib import Path

from aws_stepfunctions_toolkit import (
    WorkflowRunner,
    StaticMockResponseStrategy,
    CallableStrategy,
)

# >>> **EDIT THIS** <<<
ROLE_ARN = "arn:aws:iam::000000000000:role/sfn-UnigenStateMachine-prod"

HERE = Path(__file__).parent
definition = json.loads((HERE / "state_machine.asl.json").read_text())

# A mocked lambda:invoke result must put the function's return under "Payload" as a JSON
# *string* (the toolkit $parse's it back). Return the shape the real integration would.
mock_mapping = {
    # Your own function — gets the step's input, returns its (mocked) result:
    "Enrich": CallableStrategy(lambda data: {"Payload": json.dumps({"enriched": True})}),
    # A fixed payload:
    "Notify": StaticMockResponseStrategy(json.dumps({"Payload": json.dumps({"notified": True})})),
}

runner = WorkflowRunner(
    role_arn=ROLE_ARN,
    asl_registry={"main": definition},
    mock_mapping=mock_mapping,
)

final_output = runner.start(initial_input={"order_id": 123})
print(json.dumps(final_output, indent=2))
