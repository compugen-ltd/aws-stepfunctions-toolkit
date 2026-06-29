# Setup

The toolkit calls the **real** AWS `test_state` API for the engine logic, so two things must be
in place before anything runs. A third (Docker) is only needed if you run steps in containers.

> All examples in this project use [`uv`](https://docs.astral.sh/uv/) — e.g.
> `uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py`, which pulls the toolkit
> in on the fly (no virtualenv to manage). Install it first (below).

## 0. Install uv

```bash
# Ubuntu / Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

(Or `pip install uv` / `pipx install uv` if you prefer.) Verify with `uv --version`.

## 1. AWS credentials and a region

Any standard AWS SDK setup works — the toolkit uses your ambient boto3 session. Pick one:

```bash
# Environment variables
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...        # if using temporary creds
export AWS_REGION=us-east-1

# ...or a named profile / SSO
aws configure                       # writes ~/.aws/credentials + config
aws sso login --profile my-profile
export AWS_PROFILE=my-profile
```

Region resolution order: the `region=` argument to `WorkflowRunner` → `AWS_REGION` → your AWS
config. If none is set, boto3 raises `NoRegionError`.

Verify:

```bash
aws sts get-caller-identity
```

## 2. A role for `test_state` (the `role_arn` you pass)

`test_state` runs each state under an IAM **execution role** that you pass as `role_arn`. You need:

- **The role itself**, trusted by Step Functions.
- **Permission for your caller** to call `states:TestState` and to `iam:PassRole` that role.

### Create the execution role

`trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "states.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

```bash
aws iam create-role \
  --role-name sfn-toolkit-test-state \
  --assume-role-policy-document file://trust-policy.json
```

For a fully **mocked** run (the [quickstart](../examples/quickstart/)), the role needs no extra
permissions — the mocked steps don't actually call AWS. If you let a real integration run (e.g.
`BatchJobResponseStrategy` submitting a job), attach the permissions that integration needs.

The role ARN is then:

```
arn:aws:iam::<your-account-id>:role/sfn-toolkit-test-state
```

### Let your caller use it

Attach to the **user/role whose credentials you run with** (from step 1):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "states:TestState", "Resource": "*" },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::<your-account-id>:role/sfn-toolkit-test-state"
    }
  ]
}
```

Now set `role_arn` to that role ARN (the only value the [quickstart](../examples/quickstart/run.py)
asks you to edit).

## 3. Docker (only for container strategies)

Needed only if you use [`DockerBatchStrategy`](strategies.md#run-the-steps-container-locally) to
build/run a step's container locally. Install Docker and make sure the daemon is running:

```bash
docker info        # should succeed
```

- **Private ECR base images**: pass `login_ecr=True` to your image source, or call
  `login_to_ecr(region=...)` first.
- **`docker buildx bake`** (`BakeImage`): requires Buildx (bundled with modern Docker).
- **Private package installs during build** (CodeArtifact): set `codeartifact_domain` /
  `codeartifact_domain_owner` on `BakeImage`, or fetch a token with `get_codeartifact_token(...)`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `NoRegionError` | Set `AWS_REGION` or pass `region=` to `WorkflowRunner`. |
| `AccessDeniedException` on `TestState` | Add `states:TestState` to your caller (step 2). |
| `is not authorized to perform: iam:PassRole` | Add the `iam:PassRole` statement (step 2). |
| `The role defined ... cannot be assumed` | Fix the role's trust policy to allow `states.amazonaws.com`. |
| Docker errors from `DockerBatchStrategy` | Ensure `docker info` works; for ECR pass `login_ecr=True`. |
