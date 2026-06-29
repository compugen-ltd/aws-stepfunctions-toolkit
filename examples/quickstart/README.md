# Quickstart

A self-contained example you can copy and run as-is. No Docker needed — the task steps are
mocked, so it runs anywhere.

## Step by step

> First time on AWS? The [**Setup guide**](../../docs/setup.md) walks through configuring AWS
> credentials and creating the `ROLE_ARN` role from scratch.

Uses [`uv`](https://docs.astral.sh/uv/). `uv run --with` pulls the toolkit in on the fly — no
virtualenv to create or activate.

**1. Get this example** — clone the repo and enter this folder (or just `cd` here if you already
have the repo):

```bash
git clone https://github.com/compugen-ltd/aws-stepfunctions-toolkit.git
cd aws-stepfunctions-toolkit/examples/quickstart
```

**2. Set your role** — an IAM role allowed to call `states:TestState`. Either export it (the
script reads `ROLE_ARN` from the environment):

```bash
export ROLE_ARN=arn:aws:iam::<account>:role/<your-test-state-role>
# Windows PowerShell:  $env:ROLE_ARN = "arn:aws:iam::<account>:role/<your-test-state-role>"
```

…or edit the default on the `>>> **EDIT THIS** <<<` line in `run.py`. Also make sure AWS
credentials + a region are in your environment (env vars, `~/.aws`, SSO).

**3. Run it:**

```bash
uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py
```

Expected output:

```json
{
  "order_id": 123,
  "status": "ready",
  "enriched": true,
  "notified": true
}
```

## What's here

- [`state_machine.asl.json`](state_machine.asl.json) — a tiny pipeline: a `Pass` state followed
  by two task steps.
- [`run.py`](run.py) — loads the definition, mocks the two task steps (one with a function via
  `CallableStrategy`, one with a fixed payload via `StaticMockResponseStrategy`), and runs it.

From here, swap any step's strategy — e.g. run a real container with `DockerBatchStrategy` — see
the [strategies docs](../../docs/strategies.md).
