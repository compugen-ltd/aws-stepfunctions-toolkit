# Example: container-side handler (`BatchJobInterface`)

Shows the code that runs *inside* a job container, written with
[`BatchJobInterface`](../../docs/container-handler.md): parse input → (maybe skip) → run →
respond. Here it runs locally as a subprocess; the same code runs unchanged in a real container
(both honor the `OUTPUT_PATH` / task-token contract).

## Files

- [`job/main.py`](job/main.py) — a `BatchJobInterface` subclass with its own input/output models.
- [`state_machine.asl.json`](state_machine.asl.json) — one `batch:submitJob.sync` step.
- [`run.py`](run.py) — runs the job via `LocalExecutionStrategy` (no Docker).

## What to do

1. New to AWS setup? See the [Setup guide](../../docs/setup.md).
2. Open [`run.py`](run.py) and set `ROLE_ARN`. **That's the only value you must change.**
3. Run it:

```bash
pip install aws-stepfunctions-toolkit
python run.py
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
