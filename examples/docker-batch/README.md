# Example: Docker batch steps + image sources

Runs a small pipeline where a Batch (`.sync`) step executes in a **real local container** via
[`DockerBatchStrategy`](../../docs/strategies.md#run-the-steps-container-locally), built from a
plain Dockerfile ([`DockerfileImage`](../../docs/strategies.md#image-sources)). It also runs a
**nested state machine** (`startExecution.sync:2`, the `child_flow` step) and a **Lambda** step.

To build the same container via `docker buildx bake` instead, swap the `image_source` to
`BakeImage` — there's a commented example in [`run.py`](run.py), and the bake file is included.

### Per-SFN step overrides (hierarchical keys)

The `main` machine and the nested `child_flow` machine reuse the **same step names**
(`example_batch_1`, `example_batch_2`, `example_lambda_1`). In `mock_mapping`, a flat key
(`"example_batch_1"`) matches a step **anywhere**, while a hierarchical key
(`"child_flow/example_batch_1"`) overrides **only that occurrence**. `run.py` uses this so the
parent's `example_batch_1` builds a real container while the child's same-named steps are mocked
(see [Control flow → hierarchical keys](../../docs/control-flow.md#hierarchical-keys)).

## Files

- [`asl_definitions/`](asl_definitions/) — this example's own ASL: `main.asl.json` (parent) and
  `child.asl.json` (the nested machine).
- [`project_file/`](project_file/) — the per-step build contexts (`example_batch_1`,
  `example_batch_2`, `example_lambda_1`), each a tiny Dockerfile + script.
- [`docker-bake.hcl`](docker-bake.hcl) — bake targets for the `BakeImage` alternative.
- [`run.py`](run.py) — the basic version: the nested `child_flow` step is mocked with a
  `StaticMockResponseStrategy`.
- [`run_with_overrides.py`](run_with_overrides.py) — runs the nested `child_flow` machine for
  real and uses hierarchical `child_flow/<step>` keys to override its same-named steps.

## Requirements

- **Docker running** — this example builds and runs a real container (`docker info` must work).
- AWS credentials + a region and an IAM role allowed to call `test_state` — see the
  [Setup guide](../../docs/setup.md).

## What to do

1. Set your `test_state` role: `export ROLE_ARN=arn:aws:iam::<account>:role/<your-test-state-role>` (or edit the default in the script).
2. Run either version:

```bash
uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py                  # child_flow mocked
uv run --python=3.13 --with aws-stepfunctions-toolkit python run_with_overrides.py   # child runs, per-step overrides
```

Both build the `example_batch_1` container, run it locally, and feed each step's output to the
next. Swap any step to a mock / `CallableStrategy` / `LocalExecutionStrategy` to run without
Docker — see [Selecting how each step runs](../../docs/strategies.md).
