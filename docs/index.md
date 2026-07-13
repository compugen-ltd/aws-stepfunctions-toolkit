# AWS Step Functions Toolkit

**Run a Step Functions state machine end-to-end on your laptop — and choose, per step, how each one runs.**

This package was created out of the need to test a Step Functions pipeline built almost entirely
from `batch:submitJob.sync` steps. AWS's
[`test_state`](https://docs.aws.amazon.com/step-functions/latest/apireference/API_TestState.html)
API can't run `.sync` integrations (or `.waitForTaskToken`), and deploying the real state machine
to AWS to check each change was far too slow.

So instead, this toolkit walks your real ASL definition state-by-state, uses `test_state` for the
engine logic (Path/Parameters/ResultSelector/Output + next state), and lets you plug in a
**strategy** for the steps it can't run — usually by building and running that step's container
**locally with Docker**. Run a whole pipeline locally and swap any step between a mock, your own
function, a local container, or a real AWS call.

## Install

```bash
pip install aws-stepfunctions-toolkit
```

## Quick start

The snippet below shows the **shape** of a run — it is not runnable on its own (you supply your
own state machine). The runnable starter lives in
[`examples/quickstart/`](https://github.com/compugen-ltd/aws-stepfunctions-toolkit/tree/master/examples/quickstart)
(set `ROLE_ARN` and `python run.py`; no Docker — its task steps are mocked). See the
[Setup guide](setup.md) for AWS credentials and the `test_state` IAM role.

```python
import json
from aws_stepfunctions_toolkit import WorkflowRunner, StaticMockResponseStrategy, CallableStrategy

# Bring your own: your Step Functions state machine, exported as Amazon States Language (ASL) JSON.
definition = json.loads(open("state_machine.asl.json").read())

# For each step you don't want to run for real, say how to produce its result.
mock_mapping = {
    "Enrich": CallableStrategy(lambda data: {"Payload": json.dumps({"enriched": True})}),
    "Notify": StaticMockResponseStrategy(json.dumps({"Payload": json.dumps({"status": "sent"})})),
}

runner = WorkflowRunner(
    # Each state machine carries its own execution role (the role its states run under).
    asl_registry={
        "main": {**definition, "ROLE_ARN": "arn:aws:iam::<account>:role/<role-with-test-state-perms>"},
    },
    mock_mapping=mock_mapping,
)

final_output = runner.start(initial_input={"order_id": 123})
print(final_output)
```

States **without** an entry in `mock_mapping` are handled automatically (`test_state` for ordinary
states; built-in recursion for Map / Parallel / nested state machines). To run a step in a real
local container instead of mocking it, use
[`DockerBatchStrategy`](strategies.md#run-the-steps-container-locally).

```{note}
**JSONata throughout.** The examples (and the toolkit's mock-result handling) use the
[JSONata](https://docs.aws.amazon.com/step-functions/latest/dg/transforming-data.html) query
language. Set `"QueryLanguage": "JSONata"` on **each state** (not just at the top level): the
runner tests one state at a time, so a state must declare its own query language.
```

## Documentation

```{toctree}
:maxdepth: 2
:caption: Guides

setup
how-it-works
usage
strategies
control-flow
container-handler
cli-and-history
```

```{toctree}
:maxdepth: 2
:caption: Reference

reference
```

## Requirements

- Python 3.13+
- An AWS role/credentials allowed to call `test_state` (the toolkit calls the real API for the
  engine logic).
- Docker, only if you use `DockerBatchStrategy` to run steps in containers.

New to this? The [Setup guide](setup.md) covers AWS credentials, creating the `test_state` IAM
role, and Docker, step by step.

## Examples

Each folder under
[`examples/`](https://github.com/compugen-ltd/aws-stepfunctions-toolkit/tree/master/examples) is
self-contained (its own ASL, runnable script, and README). Start with `quickstart/` (copy-and-run,
no Docker), `local-subprocess/` (run a step's code as a local subprocess), or `docker-batch/`
(real local containers plus a nested machine).

## License

See [LICENSE](https://github.com/compugen-ltd/aws-stepfunctions-toolkit/blob/master/LICENSE).
