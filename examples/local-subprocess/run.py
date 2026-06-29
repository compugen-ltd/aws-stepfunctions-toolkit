"""Local-subprocess example: run a Batch step's code on your machine (no Docker).

Set ROLE_ARN, then: python run.py   (AWS setup: ../../docs/setup.md)
"""
import json
import os
import sys
from pathlib import Path

from aws_stepfunctions_toolkit import WorkflowRunner, LocalExecutionStrategy

# >>> **EDIT THIS** <<< (or set the ROLE_ARN env var)
ROLE_ARN = os.environ.get("ROLE_ARN", "arn:aws:iam::<account>:role/<role-with-test-state-perms>")

HERE = Path(__file__).parent
definition = json.loads((HERE / "state_machine.asl.json").read_text())

mock_mapping = {
    "ProcessLocally": LocalExecutionStrategy(entrypoint=[sys.executable, str(HERE / "job" / "main.py")]),
}

runner = WorkflowRunner(role_arn=ROLE_ARN, asl_registry={"main": definition}, mock_mapping=mock_mapping)
print(json.dumps(runner.start(initial_input={"order_id": 123}), indent=2))
