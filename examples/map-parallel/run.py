"""Map + Parallel example. Set ROLE_ARN, then: python run.py

No strategies needed — the built-in StandardFlowStrategy fans the Map out and runs
each Parallel branch for you.
"""
import json
import os
from pathlib import Path

from aws_stepfunctions_toolkit import WorkflowRunner

# >>> **EDIT THIS** <<< (or set the ROLE_ARN env var)
ROLE_ARN = os.environ.get("ROLE_ARN", "arn:aws:iam::<account>:role/<role-with-test-state-perms>")

HERE = Path(__file__).parent
definition = json.loads((HERE / "state_machine.asl.json").read_text())

runner = WorkflowRunner(role_arn=ROLE_ARN, asl_registry={"main": definition}, mock_mapping={})

# The Map fans out over a list input (one ItemProcessor run per item).
print(json.dumps(runner.start(initial_input=[{"id": 1}, {"id": 2}, {"id": 3}]), indent=2))
