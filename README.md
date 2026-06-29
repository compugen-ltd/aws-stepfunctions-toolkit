# AWS Step Functions Toolkit

**Run a Step Functions state machine end-to-end on your laptop — and choose, per step, how
each one runs.**

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

A complete, **runnable** version of the snippet below lives in
[`examples/quickstart/`](examples/quickstart/) — copy that folder, set `ROLE_ARN`, and run
`python run.py`. No Docker needed; the task steps are mocked.

```python
import json
from aws_stepfunctions_toolkit import WorkflowRunner, StaticMockResponseStrategy, CallableStrategy

definition = json.loads(open("state_machine.asl.json").read())

mock_mapping = {
    # Compute a step's result with your own function:
    "Enrich": CallableStrategy(lambda data: {"Payload": {"enriched": True}}),
    # ...or return a fixed payload:
    "Notify": StaticMockResponseStrategy(json.dumps({"Payload": {"status": "sent"}})),
}

runner = WorkflowRunner(
    # The only value you must set. Needs AWS creds + a region in your environment.
    role_arn="arn:aws:iam::<account>:role/<role-with-test-state-perms>",
    asl_registry={"main": definition},   # the key "main" is required
    mock_mapping=mock_mapping,
)

final_output = runner.start(initial_input={"order_id": 123})
print(final_output)
```

States **without** an entry in `mock_mapping` are handled automatically (`test_state` for
ordinary states; built-in recursion for Map / Parallel / nested state machines). To run a step
in a real local container instead of mocking it, use
[`DockerBatchStrategy`](docs/strategies.md#run-the-steps-container-locally).

## Features

Each links to docs with a code snippet, or to a runnable example.

- **Local end-to-end runs** against your real ASL definition — no deploy. → [runnable example](examples/quickstart/run.py)
- **Per-step execution choice** — `test_state`, a static mock, your own function, a local
  subprocess, a local Docker container, or a real AWS Batch submission. → [docs/strategies.md](docs/strategies.md#strategy-catalog)
- **Pluggable image sources** — plain Dockerfile (default), prebuilt/ECR image, or `docker buildx
  bake`; bring your own. A bake file is not required. → [docs/strategies.md#image-sources](docs/strategies.md#image-sources)
- **Subflows (nested state machines)** via `startExecution.sync:2`. → [docs/control-flow.md#subflows-nested-state-machines](docs/control-flow.md#subflows-nested-state-machines)
- **Map and Parallel** — fan-out and any-depth recursion. → [docs/control-flow.md#map-states](docs/control-flow.md#map-states)
- **Run a sub-range** — start and/or stop at specific states. → [docs/control-flow.md#running-a-sub-range](docs/control-flow.md#running-a-sub-range)
- **Container-side handler** (`BatchJobInterface`) for code inside your job containers. → [docs/container-handler.md](docs/container-handler.md#example)
- **Mock generation** from a real execution, plus history inspection. → [docs/cli-and-history.md](docs/cli-and-history.md#generate-mocks-from-a-real-execution)

## Documentation

| Page | What's in it |
|------|--------------|
| [Setup](docs/setup.md) | AWS credentials, the `test_state` IAM role, and Docker. |
| [How it works](docs/how-it-works.md) | Motivation, the `test_state` gap, and the run loop. |
| [Usage walkthrough](docs/usage.md) | A complete, end-to-end worked example. |
| [Selecting how each step runs](docs/strategies.md) | The strategy catalog + image sources. |
| [Control flow](docs/control-flow.md) | Subflows, Map/Parallel, recursion, start/end control. |
| [Container-side handler](docs/container-handler.md) | `BatchJobInterface` contract. |
| [CLI & history](docs/cli-and-history.md) | `sfn-toolkit generate-mock`, `ExecutionHistory`. |

## Requirements

- Python 3.13+
- An AWS role/credentials allowed to call `test_state` (the toolkit calls the real API for the
  engine logic).
- Docker, only if you use `DockerBatchStrategy` to run steps in containers.

New to this? The [**Setup guide**](docs/setup.md) covers AWS credentials, creating the
`test_state` IAM role, and Docker, step by step.

## Examples

- [`examples/quickstart/`](examples/quickstart/) — copy-and-run starter; set `ROLE_ARN` and
  `python run.py`. No Docker (task steps are mocked). Start here.
- [`examples/run_tests.py`](examples/run_tests.py) — runs a small state machine two ways, building
  the batch container from a plain Dockerfile (`DockerfileImage`) and via `docker buildx bake`
  (`BakeImage`). `make run-example` runs them (needs Docker, AWS creds, and a `ROLE_ARN` env var).

## License

See [LICENSE](LICENSE).
