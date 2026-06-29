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
| `DockerBatchStrategy(s3_bucket, image_source, ...)` | A **local Docker container** | Actually run a Batch/`.sync` step's image on your machine. |
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

### Submit a real AWS Batch job

```python
from aws_stepfunctions_toolkit import BatchJobResponseStrategy

BatchJobResponseStrategy(
    job_queue="arn:aws:batch:<region>:<account>:job-queue/my-queue",
    job_definition="arn:aws:batch:<region>:<account>:job-definition/my-jd:1",
)
```

## Image sources

`DockerBatchStrategy` gets its image from a pluggable `ImageSource`. **A bake file is not
required** — a plain Dockerfile is the easy default.

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
