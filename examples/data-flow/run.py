"""Data flow between steps. Set ROLE_ARN, then: python run.py"""
import json
from pathlib import Path

from aws_stepfunctions_toolkit import WorkflowRunner, CallableStrategy

# >>> **EDIT THIS** <<<
ROLE_ARN = "arn:aws:iam::<account>:role/<role-with-test-state-perms>"

HERE = Path(__file__).parent
definition = json.loads((HERE / "state_machine.asl.json").read_text())

mock_mapping = {
    # The "Price" Lambda: receives the step's input, returns a (mocked) Lambda result.
    "Price": CallableStrategy(lambda data: {"Payload": {"total": round(data["amount"] * 1.1, 2)}}),
}

runner = WorkflowRunner(role_arn=ROLE_ARN, asl_registry={"main": definition}, mock_mapping=mock_mapping)
print(json.dumps(runner.start(initial_input={"order_id": 123, "amount": 100}), indent=2))
