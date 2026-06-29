# Quickstart

A self-contained example you can copy and run as-is. No Docker needed — the task steps are
mocked, so it runs anywhere.

## Run it

> First time on AWS? The [**Setup guide**](../../docs/setup.md) walks through configuring AWS
> credentials and creating the `ROLE_ARN` role from scratch.

```bash
pip install aws-stepfunctions-toolkit
```

1. Open [`run.py`](run.py) and set `ROLE_ARN` to an IAM role allowed to call the Step Functions
   TestState API. **That's the only thing you need to change.**
2. Make sure AWS credentials and a region are available in your environment (env vars,
   `~/.aws`, SSO — the same setup any AWS SDK call needs).
3. Run it:

```bash
python run.py
```

Expected output:

```json
{
  "order_id": 123,
  "status": "ready",
  "enrichment": { "enriched": true },
  "notification": { "status": "sent" }
}
```

## What's here

- [`state_machine.asl.json`](state_machine.asl.json) — a tiny pipeline: a `Pass` state followed
  by two task steps.
- [`run.py`](run.py) — loads the definition, mocks the two task steps (one with a function via
  `CallableStrategy`, one with a fixed payload via `StaticMockResponseStrategy`), and runs it.

From here, swap any step's strategy — e.g. run a real container with `DockerBatchStrategy` — see
the [strategies docs](../../docs/strategies.md).
