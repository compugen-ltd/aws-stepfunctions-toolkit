"""Quickstart: run a small Step Functions state machine locally.

Set ROLE_ARN, then: uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py
No Docker — the task steps are mocked. AWS setup: ../../docs/setup.md
"""

import json
import os
from pathlib import Path

from aws_stepfunctions_toolkit import (
    WorkflowRunner,
    StaticMockResponseStrategy,
    CallableStrategy,
)

# >>> **EDIT THIS** <<< (or set the ROLE_ARN env var)
ROLE_ARN = os.environ.get(
    "ROLE_ARN", "arn:aws:iam::<account>:role/<role-with-test-state-perms>"
)

HERE = Path(__file__).parent
definition = json.loads((HERE / "state_machine.asl.json").read_text())

# A mocked lambda:invoke result must put the function's return under "Payload" as a JSON
# *string* (the toolkit $parse's it back). Return the shape the real integration would.
mock_mapping = {
    # Your own function — gets the step's input, returns its (mocked) result:
    "Enrich": CallableStrategy(
        lambda data: {"Payload": json.dumps({"enriched": True})}
    ),
    # A fixed payload:
    "Notify": StaticMockResponseStrategy(
        json.dumps({"Payload": json.dumps({"notified": True})})
    ),
}

runner = WorkflowRunner(
    # Each state machine carries its own execution role (the role its states run under).
    asl_registry={"main": {**definition, "ROLE_ARN": ROLE_ARN}},
    mock_mapping=mock_mapping,
)

final_output = runner.start(initial_input={"order_id": 123})
print(json.dumps(final_output, indent=2))
