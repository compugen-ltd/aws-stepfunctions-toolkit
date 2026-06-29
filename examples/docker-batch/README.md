# Example: Docker batch steps + image sources

Runs a small pipeline where a Batch (`.sync`) step executes in a **real local container** via
[`DockerBatchStrategy`](../../docs/strategies.md#run-the-steps-container-locally), built from a
plain Dockerfile ([`DockerfileImage`](../../docs/strategies.md#image-sources)). The other steps
are mocked (a function, a fixed Lambda payload, and the `startExecution.sync:2` wrapper).

To build the same container via `docker buildx bake` instead, swap the `image_source` to
`BakeImage` — there's a commented example in [`run.py`](run.py), and the bake file is included.

## Files

- [`asl_definitions/`](asl_definitions/) — this example's own ASL: `main.asl.json` (parent) and
  `child.asl.json` (the nested machine).
- [`project_file/`](project_file/) — the per-step build contexts (`example_batch_1`,
  `example_batch_2`, `example_lambda_1`), each a tiny Dockerfile + script.
- [`docker-bake.hcl`](docker-bake.hcl) — bake targets for the `BakeImage` alternative.
- [`run.py`](run.py) — wires the runner up and runs the machine.

## Requirements

- **Docker running** — this example builds and runs a real container (`docker info` must work).
- AWS credentials + a region and an IAM role allowed to call `test_state` — see the
  [Setup guide](../../docs/setup.md).

## What to do

1. Set your `test_state` role: `export ROLE_ARN=arn:aws:iam::<account>:role/<your-test-state-role>` (or edit the default in [`run.py`](run.py)).
2. Run it:

```bash
uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py
```

It builds the `example_batch_1` container, runs it locally, and feeds each step's output to the
next. Swap any step to a mock / `CallableStrategy` / `LocalExecutionStrategy` to run without
Docker — see [Selecting how each step runs](../../docs/strategies.md).
