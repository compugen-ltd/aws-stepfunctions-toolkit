# Example: mock generation from a real execution

Capture a real, completed Step Functions execution and turn its per-state outputs into mock data
you can replay locally — plus basic history inspection. See
[CLI & history](../../docs/cli-and-history.md).

## Requirements

AWS credentials + a region (see the [Setup guide](../../docs/setup.md)) and a **real, completed
execution ARN** of one of your own state machines. There's no bundled ASL, and **no `role_arn`**
is needed — this only reads the execution. No Docker.

## What to do

Point it at one of your executions via the `EXECUTION_ARN` env var:

```bash
EXECUTION_ARN=arn:aws:states:<region>:<account>:execution:MyStateMachine:run-1 \
  uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py
```

This writes `mock_data/{history.json,input.json,state_outputs.json}`. `state_outputs.json` holds
each state's recorded output, ready to back `StaticMockResponseStrategy` entries when you wire up
a [runner](../quickstart/). Pair with [running a sub-range](../sub-range/) to replay a failure
from the middle of a real run.

The same thing from the CLI:

```bash
uv run --with aws-stepfunctions-toolkit sfn-toolkit generate-mock \
  arn:aws:states:<region>:<account>:execution:MyStateMachine:run-1
```
