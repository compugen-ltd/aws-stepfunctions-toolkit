# Example: local subprocess (no Docker)

Runs a Batch (`.sync`) step's code **directly on your machine as a subprocess** — no Docker —
using [`LocalExecutionStrategy`](../../docs/strategies.md#run-the-step-locally-as-a-subprocess-no-docker).
Fast inner loop; switch the same step to `DockerBatchStrategy` later to run the real image.

## Files

- [`state_machine.asl.json`](state_machine.asl.json) — one `batch:submitJob.sync` step.
- [`job/main.py`](job/main.py) — the "job": reads its input arg, writes result JSON to `OUTPUT_PATH`.
- [`run.py`](run.py) — maps the step to `LocalExecutionStrategy(entrypoint=["python", "job/main.py"])` and runs the machine.

## Requirements

AWS credentials + a region and an IAM role allowed to call `test_state` — see the
[Setup guide](../../docs/setup.md). No Docker (the job runs as a local subprocess).

## What to do

1. Set `ROLE_ARN` in [`run.py`](run.py) to your `test_state` role.
2. Run it:

```bash
uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py
```

Expected output (the job's payload merged with the input):

```json
{
  "order_id": 123,
  "processed": true,
  "input_seen": { "order_id": 123 }
}
```

## How it works

`LocalExecutionStrategy` resolves the step's `Command`/`Environment` from the ASL (via the test
API), prepends your `entrypoint`, sets `OUTPUT_PATH` to a temp file, runs the process, and uses
whatever it writes there as the step's result — then `test_state` applies the state's `Output`.
The job honors the same `OUTPUT_PATH` contract a real container would (see
[Container-side handler](../../docs/container-handler.md)).
