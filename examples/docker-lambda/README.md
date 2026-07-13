# Example: run a real Lambda container image (via the RIE)

Runs a `lambda:invoke` step by executing the Lambda's **real container image** locally, instead
of hand-writing a mock. [`DockerLambdaStrategy`](../../docs/strategies.md#run-a-lambda-container-image-via-rie)
builds the image from a plain Dockerfile ([`DockerfileImage`](../../docs/strategies.md#image-sources)),
runs it detached with the AWS **Runtime Interface Emulator** (RIE) port published, POSTs the
resolved event `Payload`, and returns the handler's real output — the Lambda counterpart to
[`DockerBatchStrategy`](../../docs/strategies.md#run-the-steps-container-locally).

The AWS Lambda base images (`public.ecr.aws/lambda/python:*`, etc.) ship the RIE, so no extra
tooling is needed: the strategy `POST`s the event to
`/2015-03-31/functions/function/invocations`.

## Files

- [`asl_definitions/main.asl.json`](asl_definitions/main.asl.json) — one `lambda:invoke` state.
  Its `Output` keeps the **real** `$states.result.Payload` expression; the runner rewrites it to
  `$parse(...)` for the mocked step (the mocked result's `Payload` is a JSON string).
- [`project_file/echo_lambda/`](project_file/echo_lambda/) — a tiny Lambda image: an `app.py`
  handler that doubles `number` and echoes the event, plus a minimal Dockerfile.
- [`run.py`](run.py) — wires the step to `DockerLambdaStrategy`.

## Requirements

- **Docker running** — this example builds and runs a real Lambda container (`docker info` must work).
- AWS credentials + a region and an IAM role allowed to call `test_state` — see the
  [Setup guide](../../docs/setup.md).

## What to do

1. Set your `test_state` role: `export ROLE_ARN=arn:aws:iam::<account>:role/<your-test-state-role>` (or edit the default in the script).
2. Run it:

```bash
uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py
```

Expected output:

```json
{
  "doubled": 42,
  "echo": { "number": 21 }
}
```
