"""Container-side handler example. Set ROLE_ARN, then: python run.py

The job in job/main.py uses BatchJobInterface; here it runs locally as a subprocess.
The same code runs unchanged in a real container (swap to DockerBatchStrategy).
"""

import json
import os
import sys
from pathlib import Path

from aws_stepfunctions_toolkit import WorkflowRunner, LocalExecutionStrategy

# >>> **EDIT THIS** <<< (or set the ROLE_ARN env var)
ROLE_ARN = os.environ.get(
    "ROLE_ARN", "arn:aws:iam::<account>:role/<role-with-test-state-perms>"
)

HERE = Path(__file__).parent
definition = json.loads((HERE / "state_machine.asl.json").read_text())

mock_mapping = {
    "RunJob": LocalExecutionStrategy(
        entrypoint=[sys.executable, str(HERE / "job" / "main.py")]
    ),
}

runner = WorkflowRunner(
    asl_registry={"main": {**definition, "ROLE_ARN": ROLE_ARN}},
    mock_mapping=mock_mapping,
)
print(json.dumps(runner.start(initial_input={"order_id": 123}), indent=2))
