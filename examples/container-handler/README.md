# Example: container-side handler (`BatchJobInterface`)

Shows the code that runs *inside* a job container, written with
[`BatchJobInterface`](../../docs/container-handler.md): parse input → (maybe skip) → run →
respond. Here it runs locally as a subprocess; the same code runs unchanged in a real container
(both honor the `OUTPUT_PATH` / task-token contract).

## Files

- [`job/main.py`](job/main.py) — a `BatchJobInterface` subclass with its own input/output models.
- [`state_machine.asl.json`](state_machine.asl.json) — one `batch:submitJob.sync` step.
- [`run.py`](run.py) — runs the job via `LocalExecutionStrategy` (no Docker).

## Requirements

AWS credentials + a region and an IAM role allowed to call `test_state` — see the
[Setup guide](../../docs/setup.md). No Docker (the job runs as a local subprocess).

## What to do

1. Set `ROLE_ARN` in [`run.py`](run.py) to your `test_state` role.
2. Run it:

```bash
uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py
```

Expected output:

```json
{
  "order_id": 123,
  "status": "processed"
}
```

To run the same handler in a real container instead, build an image whose entrypoint is
`python main.py` and switch the step to `DockerBatchStrategy` — see
[Selecting how each step runs](../../docs/strategies.md).
