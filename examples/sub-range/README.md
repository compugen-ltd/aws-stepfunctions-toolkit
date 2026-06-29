# Example: run a sub-range

Run the whole machine, or just part of it, with `start` / `end` on `runner.start(...)`. Useful for
reproducing a failure from the middle of a long pipeline without re-running the earlier steps
(pair it with mocks captured from a real run — see [CLI & history](../../docs/cli-and-history.md)).
See [Control flow → running a sub-range](../../docs/control-flow.md#running-a-sub-range).

## Files

- [`state_machine.asl.json`](state_machine.asl.json) — a linear `Step1 → Step2 → Step3` pipeline.
- [`run.py`](run.py) — runs it three ways: whole machine, only `Step2`, and `Step2`→end.

## What to do

1. New to AWS setup? See the [Setup guide](../../docs/setup.md).
2. Open [`run.py`](run.py) and set `ROLE_ARN`. **That's the only value you must change.**
3. Run it:

```bash
pip install aws-stepfunctions-toolkit
python run.py
```

- `runner.start(input)` — whole machine (`Step1` → `Step3`).
- `runner.start(input, start="Step2", end="Step2")` — only `Step2`.
- `runner.start(input, start="Step2")` — from `Step2` to the end.
