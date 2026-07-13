# Selecting how each step runs

Every state the runner visits gets a **strategy** that supplies its result. You assign
strategies per state via `mock_mapping={state_name: strategy}`. A state with no mapping is
handled by the default `StandardFlowStrategy` (see [Control flow](control-flow.md)).

This is the core idea: **the same workflow can run with each step backed by a different
"means"** — AWS-evaluated, mocked, your own function, a local container, or a real AWS call —
and you can change a step's means without touching the ASL.

## Strategy catalog

| Strategy | The "means" | Use it when |
|----------|-------------|-------------|
| *(no mapping)* → `StandardFlowStrategy` | `test_state` evaluates the state; Map/Parallel/subflows recursed | Pass/Choice/Wait/Succeed/Fail and any state whose logic the API can run. |
| `StaticMockResponseStrategy(result)` | A fixed JSON string | You just need a step to "return X" so the flow proceeds. |
| `CallableStrategy(handler)` | Your Python function, in-process | Compute a result from the input without a container. |
| `LocalExecutionStrategy(entrypoint, ...)` | A **local subprocess** (no Docker) | Run the step's code directly in your terminal. |
| `DockerBatchStrategy(s3_bucket, image_source, ...)` | A **local Docker container** | Actually run a Batch/`.sync` step's image on your machine. |
| `DockerLambdaStrategy(image_source, ...)` | A **local Lambda container** (via the RIE) | Actually run a `lambda:invoke` step's real image and assert on its real output. |
| `BatchJobResponseStrategy(job_queue, job_definition, ...)` | A **real AWS Batch** submission | Exercise the step remotely in AWS. |
| `GetLatestConfigurationStrategy(application, environment, configuration_profile)` | A **real AWS AppConfig** fetch | The step reads live AppConfig. |
| `AbstractMockMapResponseStrategy` (subclass) | Custom Map item selection | A Map state's items come from a non-obvious place in the input. |

### Static mock

```python
from aws_stepfunctions_toolkit import StaticMockResponseStrategy
# Lambda steps wrap their result in a Payload:
StaticMockResponseStrategy('{"Payload": {"statusCode": 200, "body": {"ok": true}}}')
```

### Your own function (the simplest custom handler)

```python
from aws_stepfunctions_toolkit import CallableStrategy

# Return a dict/list (json-encoded for you) or a pre-serialized JSON string.
CallableStrategy(lambda input_data: {**input_data, "decorated": True})
```

For full control, subclass `StateExecutionStrategy`:

```python
import json
from aws_stepfunctions_toolkit import StateExecutionStrategy

class MyStrategy(StateExecutionStrategy):
    def execute(self, state_name, state_def, input_data, orchestrator, context=None, parent_path=""):
        result = my_logic(input_data)          # do anything
        return {"mock": {"result": json.dumps(result)}, "context": context}
```

### Run the step locally as a subprocess (no Docker)

```python
from aws_stepfunctions_toolkit import LocalExecutionStrategy

# Resolves the step's Command/Environment from the ASL, prepends `entrypoint`
# (the local equivalent of the image's ENTRYPOINT), injects OUTPUT_PATH, runs it,
# and reads the JSON the process writes to that path.
LocalExecutionStrategy(
    entrypoint=["python", "jobs/process_data/main.py"],
    cwd=".",                       # optional working directory
    extra_env={"LOG_LEVEL": "DEBUG"},   # optional extra env vars
)
```

The same job code runs unchanged here or in a container — both honor the `OUTPUT_PATH` contract
(see [Container-side handler](container-handler.md)). Use this for a fast, Docker-free inner loop;
switch the step to `DockerBatchStrategy` when you want the real image.

### Run the step's container locally

```python
from aws_stepfunctions_toolkit import DockerBatchStrategy, DockerfileImage

DockerBatchStrategy(
    s3_bucket="my-bucket",
    image_source=DockerfileImage(context="./jobs/process_data"),
    volumes=[("/host/data", "/data")],     # optional bind mounts
    variables={"workfolder": "/data"},     # optional, for resolving the step's overrides
    gpus="all",                            # optional
)
```

`DockerBatchStrategy` resolves the step's `Command` + `Environment` from the ASL (via
`test_state`), runs the container, and reads its output. The container must write its result
JSON to `/tmp/output.json`; the toolkit mounts a writable temp dir at `/tmp` and injects
`OUTPUT_PATH` and `S3_OUTPUT_PATH`. See [Container-side handler](container-handler.md) for the
in-container contract and `BatchJobInterface`.

### Run a Lambda container image via RIE

```python
from aws_stepfunctions_toolkit import DockerLambdaStrategy, DockerfileImage

DockerLambdaStrategy(
    image_source=DockerfileImage(context="./jobs/my_lambda"),
    extra_run_envs={"LOG_LEVEL": "DEBUG"},   # optional extra container env
    forward_aws_envs=True,                   # forward AWS_* so the handler's AWS calls work (default)
    startup_timeout=30.0,                    # seconds to wait for the RIE to answer (default)
)
```

The Lambda counterpart to `DockerBatchStrategy`: instead of faking a `lambda:invoke` step with a
mock, it runs the Lambda's **real image** and returns the handler's real output. AWS Lambda base
images (`public.ecr.aws/lambda/python:*`, etc.) ship the **Runtime Interface Emulator** (RIE),
which serves `POST /2015-03-31/functions/function/invocations`. The strategy resolves the event
`Payload` the state would pass (via `test_state`), runs the image detached with the RIE port
published, `POST`s the event, and returns the handler response wrapped as the Step Functions
`lambda:invoke` result shape (`{"Payload": <json-string>}`) — so your ASL's real
`$states.result.Payload` expression resolves (the runner rewrites it to `$parse(...)` for the
mocked step). Uses the same [image sources](#image-sources) as `DockerBatchStrategy`. See the
[`docker-lambda` example](https://github.com/compugen-ltd/aws-stepfunctions-toolkit/blob/master/examples/docker-lambda/run.py).

### Submit a real AWS Batch job

```python
from aws_stepfunctions_toolkit import BatchJobResponseStrategy

BatchJobResponseStrategy(
    job_queue="arn:aws:batch:<region>:<account>:job-queue/my-queue",
    job_definition="arn:aws:batch:<region>:<account>:job-definition/my-jd:1",
)
```

## Image sources

`DockerBatchStrategy` and `DockerLambdaStrategy` get their image from a pluggable `ImageSource`.
**A bake file is not required** — a plain Dockerfile is the easy default.

| Image source | Build/obtain by |
|--------------|-----------------|
| `DockerfileImage(context, dockerfile=None, build_args=None, tag=None, target=None, login_ecr=False, region=None)` | `docker build` of a Dockerfile + context (the common path). |
| `PrebuiltImage(image, login_ecr=False, region=None)` | Run an existing local image or pull one (set `login_ecr=True` for private ECR). |
| `BakeImage(bake_file, target, tag=None, base_dir=None, bake_variables=None, codeartifact_domain=None, codeartifact_domain_owner=None, region=None)` | `docker buildx bake` for monorepo/advanced builds. Set `base_dir` for the bake `BASE_DIR` var; set `codeartifact_*` to inject a `CODEARTIFACT_AUTH_TOKEN` build var for private package installs. |

Write your own by implementing `ensure_image()`:

```python
from aws_stepfunctions_toolkit import ImageSource

class MyImage(ImageSource):
    def ensure_image(self) -> str:
        # build / pull however you like
        return "my-image:latest"     # return a locally-runnable image ref
```

Helpers `login_to_ecr(region=None)` and `get_codeartifact_token(domain, domain_owner, region=None)`
are exported for custom sources.

## Targeting a specific occurrence of a step

If the same state name appears in more than one place (e.g. inside two subflows or a Map), use a
**hierarchical key** `"ParentPath/StateName"` in `mock_mapping` to target one occurrence; a plain
`"StateName"` key matches it anywhere. See [Control flow](control-flow.md#hierarchical-keys).
