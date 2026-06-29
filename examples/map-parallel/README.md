# Example: Map & Parallel

Shows the built-in handling of composite states: a **Map** (fan-out over input items) followed by
a **Parallel** (concurrent branches). You write no strategies — the default `StandardFlowStrategy`
recurses into the `ItemProcessor` and each branch for you. See
[Control flow](../../docs/control-flow.md#map-states).

## Files

- [`state_machine.asl.json`](state_machine.asl.json) — a `Map` state then a `Parallel` state.
- [`run.py`](run.py) — runs it with an empty `mock_mapping` (nothing to mock).

## Requirements

AWS credentials + a region and an IAM role allowed to call `test_state` — see the
[Setup guide](../../docs/setup.md). No Docker.

## What to do

1. Set your `test_state` role: `export ROLE_ARN=arn:aws:iam::<account>:role/<your-test-state-role>` (or edit the default in [`run.py`](run.py)).
2. Run it:

```bash
uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py
```

The `Map` runs its `ItemProcessor` once per item in the list input; the `Parallel` then runs both
branches and collects their results. Maps and Parallels nest to any depth — same mechanism.
