"""Local-subprocess example: run a Batch step's code directly on your machine (no Docker).

Copy this folder, set ROLE_ARN, then run:  python run.py

`LocalExecutionStrategy` resolves the step's Command/Environment from the ASL, prepends
`entrypoint` (the program to run), injects OUTPUT_PATH, runs it as a subprocess, and reads
the JSON the process writes back. The job script lives in job/main.py.
"""
import json
import sys
from pathlib import Path

from aws_stepfunctions_toolkit import WorkflowRunner, LocalExecutionStrategy

# EDIT THIS — an IAM role allowed to call states:TestState. (Needs AWS creds + a region too;
# see ../../docs/setup.md.)
ROLE_ARN = "arn:aws:iam::<account>:role/<role-with-test-state-perms>"

HERE = Path(__file__).parent
definition = json.loads((HERE / "state_machine.asl.json").read_text())

mock_mapping = {
    "ProcessLocally": LocalExecutionStrategy(
        entrypoint=[sys.executable, str(HERE / "job" / "main.py")],
    ),
}

runner = WorkflowRunner(
    role_arn=ROLE_ARN,
    asl_registry={"main": definition},
    mock_mapping=mock_mapping,
)

final_output = runner.start(initial_input={"order_id": 123})
print(json.dumps(final_output, indent=2))
