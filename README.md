# AWS Step Functions Toolkit

**Run a Step Functions state machine end-to-end on your laptop — and choose, per step, how
each one runs.**

The motivation to create this package was the need to test a Step Functions pipeline built almost
entirely from `batch:submitJob.sync` steps. AWS's
[`test_state`](https://docs.aws.amazon.com/step-functions/latest/apireference/API_TestState.html)
API does not currently support `.sync` integrations or `.waitForTaskToken`, and deploying and
running the state machine on AWS to validate each change made iterating impractical.

AWS's docs suggest [chaining `test_state` calls](https://docs.aws.amazon.com/step-functions/latest/dg/test-state-isolation.html#iterating-through-state-machine-definitions)
— feeding each state's output and next state into the next call — to exercise a complete execution
path, but leave you to build that driver loop yourself. This toolkit packages that logic as a
framework so you don't have to: it walks your real ASL definition state by state, delegates the
engine logic (Path/Parameters/ResultSelector/Output and next-state resolution) to `test_state`,
and handles the parts that aren't a linear chain — Map and Parallel fan-out, any-depth recursion,
and nested subflows. For the steps `test_state` cannot run (`.sync`, `.waitForTaskToken`), you
plug in a **strategy** — typically by building and running that step's container **locally with
Docker**. The result: run an entire pipeline locally and swap any step between a mock, your own
function, a local container, or a real AWS call.

<p align="center">
  <img src="docs/overview.svg" alt="Annotated Step Functions workflow showing how the toolkit runs each state type: test_state for engine logic, a strategy (e.g. local Docker) for .sync steps, and recursion for nested subflows" width="820">
</p>

<sub>The real console graph of the <a href="examples/docker-batch/">docker-batch</a> example, annotated to show how the toolkit handles each state.</sub>

## Install

```bash
pip install aws-stepfunctions-toolkit
```

## Quick start

To run the bundled quickstart example (no Docker — its task steps are mocked), head to
[`examples/quickstart/`](examples/quickstart/) — it has step-by-step instructions. You'll need
AWS credentials + a region and an IAM role allowed to call `test_state` (see the
[Setup guide](docs/setup.md)).

### What your code looks like

The snippet below shows the **shape** of a run — it is not runnable on its own (you supply your
own state machine); the quickstart folder above is the runnable version.

```python
import json
from aws_stepfunctions_toolkit import WorkflowRunner, StaticMockResponseStrategy, CallableStrategy

# Bring your own: your Step Functions state machine, exported as Amazon States Language (ASL)
# JSON. (In the AWS console: the state machine's "Definition" tab. This is the workflow you
# want to test — the toolkit does not generate it for you.)
definition = json.loads(open("state_machine.asl.json").read())

# For each step you don't want to run for real, say how to produce its result. Keys are the
# state names from your definition.
mock_mapping = {
    # A mocked lambda:invoke result puts the function's return under "Payload" as a JSON string.
    "Enrich": CallableStrategy(lambda data: {"Payload": json.dumps({"enriched": True})}),          # your own function
    "Notify": StaticMockResponseStrategy(json.dumps({"Payload": json.dumps({"status": "sent"})})),  # a fixed payload
}

runner = WorkflowRunner(
    role_arn="arn:aws:iam::<account>:role/<role-with-test-state-perms>",  # the only value you must set; needs AWS creds + a region in your environment
    asl_registry={"main": definition},
    mock_mapping=mock_mapping,
)

final_output = runner.start(initial_input={"order_id": 123})
print(final_output)
```

`asl_registry` maps state-machine names to their ASL definitions: put the workflow you're testing
under the key **`"main"`** (the entry point). If your machine starts nested state machines (via
`startExecution.sync:2`), register each one too, keyed by the name of the state that starts it —
see [Control flow](docs/control-flow.md#subflows-nested-state-machines).

> **JSONata throughout.** The examples (and the toolkit's mock-result handling) use the
> [JSONata](https://docs.aws.amazon.com/step-functions/latest/dg/transforming-data.html) query
> language. Set `"QueryLanguage": "JSONata"` on **each state** (not just at the top level): the
> runner tests one state at a time, so a state must declare its own query language.

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

Each folder under [`examples/`](examples/) is self-contained (its own ASL, runnable script, and
README) — see the [examples index](examples/README.md). Start with:

- [`examples/quickstart/`](examples/quickstart/) — copy-and-run starter; set `ROLE_ARN` and
  `python run.py`. No Docker (task steps are mocked).
- [`examples/local-subprocess/`](examples/local-subprocess/) — run a step's code as a local
  subprocess (`LocalExecutionStrategy`). No Docker.
- [`examples/docker-batch/`](examples/docker-batch/) — run steps in real local containers
  (`DockerfileImage` + `BakeImage`) plus a nested machine. `make run-example` runs it (needs
  Docker, AWS creds, and a `ROLE_ARN` env var).

## License

See [LICENSE](LICENSE).
