# Quickstart

A self-contained example you can copy and run as-is. No Docker needed — the task steps are
mocked, so it runs anywhere.

## Step by step

> First time on AWS? The [**Setup guide**](../../docs/setup.md) walks through configuring AWS
> credentials and creating the `ROLE_ARN` role from scratch.

**1. Install the toolkit** (ideally in a fresh virtual environment):

```bash
python -m venv .venv && source .venv/bin/activate   # optional; on Windows: .venv\Scripts\activate
pip install aws-stepfunctions-toolkit
```

**2. Make a working directory:**

```bash
mkdir sfn-quickstart && cd sfn-quickstart
```

**3. Copy this example's two files into it** (from your clone of the repo):

```bash
cp /path/to/aws-stepfunctions-toolkit/examples/quickstart/run.py .
cp /path/to/aws-stepfunctions-toolkit/examples/quickstart/state_machine.asl.json .
```

**4. Set your role.** Open `run.py` and replace the `ROLE_ARN` value on the line marked
`>>> **EDIT THIS** <<<` with an IAM role allowed to call `states:TestState`. Make sure AWS
credentials + a region are in your environment (env vars, `~/.aws`, SSO). **That's the only edit.**

**5. Run it:**

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
