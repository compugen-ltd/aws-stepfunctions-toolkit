# Example: advanced — deployed state machine + real Lambda + local script

The realistic case: a state machine and a Lambda are **deployed to AWS**, and you run the whole
pipeline **locally** — invoking the **real** Lambda for the `Enrich` step while running the
`ProcessLocally` Batch step as a **local script** (no Batch infra needed). `run.py` loads the
**deployed** definition with `describe_state_machine`, so you're testing exactly what's deployed.

> This is the one example that provisions AWS resources. It needs Docker? No — but it does create
> a Lambda, an IAM role, and a state machine via CloudFormation, and it invokes the Lambda for
> real. See the [Setup guide](../../docs/setup.md) for credentials.

## Files

- [`infra/template.yaml`](infra/template.yaml) — CloudFormation: the Lambda (+ role), the state
  machine (+ its role), and stack outputs.
- [`job/main.py`](job/main.py) — the local script the `ProcessLocally` step runs.
- [`run.py`](run.py) — loads the deployed definition; maps `Enrich` to a real Lambda invoke and
  `ProcessLocally` to a local subprocess; runs it.

## What to do

1. **Deploy** the stack:

   ```bash
   aws cloudformation deploy \
     --template-file infra/template.yaml \
     --stack-name sfn-toolkit-advanced \
     --capabilities CAPABILITY_IAM
   ```

2. **Read the outputs** and export them:

   ```bash
   eval "$(aws cloudformation describe-stacks --stack-name sfn-toolkit-advanced \
     --query 'Stacks[0].Outputs' --output text | \
     awk '{print "export "$1"="$2}' | \
     sed 's/StateMachineArn/STATE_MACHINE_ARN/;s/FunctionArn/FUNCTION_ARN/;s/SfnRoleArn/SFN_ROLE_ARN/')"
   ```

   (Or copy them by hand: `STATE_MACHINE_ARN`, `FUNCTION_ARN`, `SFN_ROLE_ARN`.)

3. **Run** it:

   ```bash
   pip install aws-stepfunctions-toolkit
   python run.py
   ```

4. **Tear down** when done:

   ```bash
   aws cloudformation delete-stack --stack-name sfn-toolkit-advanced
   ```

## Notes

- `Enrich` runs the **real** deployed Lambda (via a `CallableStrategy` calling `lambda.invoke`).
- `ProcessLocally` runs **locally** via `LocalExecutionStrategy` — the deployed state machine
  references placeholder Batch ARNs, so it can't run that step in AWS, but locally the toolkit
  runs your script instead. Swap it to `DockerBatchStrategy` to run a real container.
