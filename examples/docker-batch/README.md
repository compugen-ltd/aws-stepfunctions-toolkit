# Example: Docker batch steps + image sources

Runs a small pipeline where Batch (`.sync`) steps execute in **real local containers** via
[`DockerBatchStrategy`](../../docs/strategies.md#run-the-steps-container-locally), and shows the
two main [image sources](../../docs/strategies.md#image-sources):

- `test_example_1` builds the container from a **plain Dockerfile** (`DockerfileImage`).
- `test_example_2` builds it via **`docker buildx bake`** (`BakeImage`).

It also exercises a **nested state machine** (`startExecution.sync:2`, the `child_flow` step) and
a **Lambda** step (mocked), so it doubles as the subflow example.

## Files

- [`asl_definitions/`](asl_definitions/) — this example's own ASL: `main.asl.json` (parent) and
  `child.asl.json` (the nested machine).
- [`docker-bake.hcl`](docker-bake.hcl) — bake targets for the `BakeImage` variant.
- [`project_file/`](project_file/) — the per-step build contexts (`example_batch_1`,
  `example_batch_2`, `example_lambda_1`), each a tiny Dockerfile + script.
- [`run_tests.py`](run_tests.py) — two pytest tests wiring the runner up both ways.

## What to do

1. Read the [Setup guide](../../docs/setup.md) for AWS credentials and the `test_state` role.
2. This example **needs Docker running**, AWS credentials, and a `ROLE_ARN` env var:

```bash
pip install "aws-stepfunctions-toolkit[examples]"
export ROLE_ARN=arn:aws:iam::<account>:role/<role-with-test-state-perms>
uv run pytest examples/docker-batch/run_tests.py        # or: make run-example
```

The tests build the example containers and run them locally, feeding each step's output to the
next. Swap any step to a mock/`CallableStrategy`/`LocalExecutionStrategy` to run without Docker —
see [Selecting how each step runs](../../docs/strategies.md).
