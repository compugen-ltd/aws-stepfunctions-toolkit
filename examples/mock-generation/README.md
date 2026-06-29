# Example: mock generation from a real execution

Capture a real, completed Step Functions execution and turn its per-state outputs into mock data
you can replay locally — plus basic history inspection. See
[CLI & history](../../docs/cli-and-history.md).

> Unlike the other examples, this one reads a **real execution**, so there's no bundled ASL — you
> point it at one of your own past executions. It needs AWS credentials + a region (see the
> [Setup guide](../../docs/setup.md)) but **no** `role_arn` (it only reads the execution).

## What to do

```bash
pip install aws-stepfunctions-toolkit
EXECUTION_ARN=arn:aws:states:<region>:<account>:execution:MyStateMachine:run-1 python run.py
```

This writes `mock_data/{history.json,input.json,state_outputs.json}`. `state_outputs.json` holds
each state's recorded output, ready to back `StaticMockResponseStrategy` entries when you wire up
a [runner](../quickstart/). Pair with [running a sub-range](../sub-range/) to replay a failure
from the middle of a real run.

The same thing from the CLI:

```bash
sfn-toolkit generate-mock arn:aws:states:<region>:<account>:execution:MyStateMachine:run-1
```
