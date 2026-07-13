"""Run a sub-range with start/end. Set ROLE_ARN, then: python run.py

See ../../docs/control-flow.md#running-a-sub-range
"""

import json
import os
from pathlib import Path

from aws_stepfunctions_toolkit import WorkflowRunner

# >>> **EDIT THIS** <<< (or set the ROLE_ARN env var)
ROLE_ARN = os.environ.get(
    "ROLE_ARN", "arn:aws:iam::<account>:role/<role-with-test-state-perms>"
)

HERE = Path(__file__).parent
definition = json.loads((HERE / "state_machine.asl.json").read_text())

runner = WorkflowRunner(
    asl_registry={"main": {**definition, "ROLE_ARN": ROLE_ARN}}, mock_mapping={}
)
initial_input = {"order_id": 123}

print("# whole machine:")
print(json.dumps(runner.start(initial_input), indent=2))

print("\n# only Step2:")
print(json.dumps(runner.start(initial_input, start="Step2", end="Step2"), indent=2))

print("\n# from Step2 to the end:")
print(json.dumps(runner.start(initial_input, start="Step2"), indent=2))
