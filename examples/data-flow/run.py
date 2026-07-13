"""Data flow between steps. Set ROLE_ARN, then: python run.py"""

import json
import os
from pathlib import Path

from aws_stepfunctions_toolkit import WorkflowRunner, CallableStrategy

# >>> **EDIT THIS** <<< (or set the ROLE_ARN env var)
ROLE_ARN = os.environ.get(
    "ROLE_ARN", "arn:aws:iam::<account>:role/<role-with-test-state-perms>"
)

HERE = Path(__file__).parent
definition = json.loads((HERE / "state_machine.asl.json").read_text())

mock_mapping = {
    # The "Price" Lambda: returns the function result under "Payload" as a JSON string
    # (the shape a real lambda:invoke produces; the toolkit $parse's it back).
    "Price": CallableStrategy(
        lambda data: {"Payload": json.dumps({"total": round(data["amount"] * 1.1, 2)})}
    ),
}

runner = WorkflowRunner(
    asl_registry={"main": {**definition, "ROLE_ARN": ROLE_ARN}},
    mock_mapping=mock_mapping,
)
print(
    json.dumps(runner.start(initial_input={"order_id": 123, "amount": 100}), indent=2)
)
