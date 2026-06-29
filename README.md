# AWS Step Functions Toolkit

**Run a Step Functions state machine end-to-end on your laptop — and choose, per step, how
each one runs.**

Iterating on a Step Functions workflow normally means deploy → run in AWS → read the execution
history → tweak → repeat. That loop is slow and costs money, and the steps that hurt most to
iterate on — `.sync` service integrations (e.g. `batch:submitJob.sync`) and
`.waitForTaskToken` callbacks — are exactly the ones AWS's
[`test_state`](https://docs.aws.amazon.com/step-functions/latest/apireference/API_TestState.html)
API **cannot** run.

This toolkit closes that gap. It walks your real ASL definition state-by-state, uses
`test_state` for the engine-side logic (InputPath / Parameters / Arguments / ResultSelector /
Output and the next-state transition), and lets you plug in a **strategy** for any step the API
can't run — most often by building and running that step's container **locally with Docker** and
feeding its output into the next state. The result: run a whole pipeline locally, swap any step
between a mock, your own function, a local container, or a real AWS call, and get a fast
edit-run loop.

> **Why this exists.** It grew out of a data pipeline built almost entirely from
> `batch:submitJob.sync` steps. The Test State API can't run `.sync` Batch jobs, so each one
> needed a workaround — and running the real state machine on AWS to check a change took far too
> long. The goal was a quick way to run the whole pipeline end-to-end on a laptop, with the
> Batch steps actually executing in local containers.

## Install

```bash
pip install aws-stepfunctions-toolkit
```

## Quick start

```python
import json
from aws_stepfunctions_toolkit import (
    WorkflowRunner, DockerBatchStrategy, DockerfileImage,
    StaticMockResponseStrategy, CallableStrategy,
)

definition = json.loads(open("my_state_machine.asl.json").read())

mock_mapping = {
    # Build this Batch step's container from a plain Dockerfile and run it locally:
    "ProcessData": DockerBatchStrategy(
        s3_bucket="my-bucket",
        image_source=DockerfileImage(context="./jobs/process_data"),
    ),
    # Return a fixed payload for a Lambda step:
    "Notify": StaticMockResponseStrategy(json.dumps({"Payload": {"ok": True}})),
    # Or compute a result with your own function:
    "Decorate": CallableStrategy(lambda input_data: {**input_data, "decorated": True}),
}

runner = WorkflowRunner(
    role_arn="arn:aws:iam::<account>:role/<role-with-test-state-perms>",
    asl_registry={"main": definition},   # the key "main" is required
    mock_mapping=mock_mapping,
    variables={"workfolder": "/data"},   # optional
    region="us-east-1",                  # optional; falls back to AWS_REGION / your AWS config
)

final_output = runner.start(initial_input={"hello": "world"})
```

Any state **without** an entry in `mock_mapping` is handled automatically (`test_state` for
ordinary states; built-in recursion for Map / Parallel / nested state machines).

## Features

- **Run a state machine locally** against your real ASL definition — no deploy. → [docs/how-it-works.md](docs/how-it-works.md)
- **Choose how each step runs** — `test_state` (AWS-evaluated), a static mock, your own Python
  function, a local Docker container, or a real AWS Batch submission. → [docs/strategies.md](docs/strategies.md)
- **Pluggable image sources** — a plain Dockerfile (the easy default), a prebuilt/ECR image, or
  `docker buildx bake`; or write your own. **A bake file is not required.** → [docs/strategies.md#image-sources](docs/strategies.md#image-sources)
- **Subflows (nested state machines)** via `startExecution.sync:2`, recursed into automatically. → [docs/control-flow.md](docs/control-flow.md)
- **Map and Parallel** states — iterated / fanned out, including custom item selection. → [docs/control-flow.md](docs/control-flow.md)
- **Recursion-safe nesting** — subflows, Maps and Parallels nest to any depth, with
  per-occurrence step targeting via hierarchical keys. → [docs/control-flow.md](docs/control-flow.md)
- **Control the start and end steps** — run the whole machine or just a sub-range. → [docs/control-flow.md#running-a-sub-range](docs/control-flow.md#running-a-sub-range)
- **A container-side handler base** (`BatchJobInterface`) for the code that runs *inside* your
  job containers — task-token or local-file response. → [docs/container-handler.md](docs/container-handler.md)
- **Generate mocks from a real execution** and inspect execution history. → [docs/cli-and-history.md](docs/cli-and-history.md)

## Documentation

| Page | What's in it |
|------|--------------|
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

## Examples

See [`examples/`](examples/): `run_tests.py` runs a small state machine two ways — building the
batch container from a plain Dockerfile (`DockerfileImage`) and via `docker buildx bake`
(`BakeImage`). `make run-example` runs them (needs Docker, AWS creds, and a `ROLE_ARN` env var).

## License

See [LICENSE](LICENSE).
