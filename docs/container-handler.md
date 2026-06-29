# Container-side handler: `BatchJobInterface`

`DockerBatchStrategy` runs your step's container and reads its result from `/tmp/output.json`.
This page is about the code that runs *inside* that container.

## The contract

A container that participates in a workflow needs to:

1. parse and validate its input,
2. optionally skip work (test mode, or "already done"),
3. run, producing a typed output,
4. **return** the result — either via a Step Functions **task token** (`.waitForTaskToken`) or
   by writing it to a local file (`OUTPUT_PATH`) so this toolkit can pick it up when running the
   container locally.

`BatchJobInterface` encapsulates exactly that. It is generic over your own pydantic models — it
makes no assumption about your input/output shape.

## Example

```python
import sys
from pydantic import BaseModel
from aws_stepfunctions_toolkit import BatchJobInterface

class In(BaseModel):
    data: str

class Out(BaseModel):
    data: str
    did_run: bool

class MyJob(BatchJobInterface[In, Out]):
    input_model = In
    output_model = Out

    def should_run(self, i: In) -> bool:
        return True

    def run(self, i: In) -> Out:
        return Out(data=i.data.upper(), did_run=True)

    def create_skip_output(self, i: In) -> Out:
        return Out(data=i.data, did_run=False)

if __name__ == "__main__":
    MyJob().execute(sys.argv[1])
```

`execute(raw_input)` runs the contract: parse → (test mode? → skip) → (`should_run`? else skip)
→ `run` → `send_response`. The skip branches call `create_skip_output`.

## How the result is returned

`send_response` chooses automatically:

- If the **task-token env var** is set (default `TaskToken`), it calls
  `stepfunctions.send_task_success(taskToken=..., output=...)` — the production
  `.waitForTaskToken` path.
- Otherwise, if the **output-path env var** is set (default `OUTPUT_PATH`), it writes the JSON
  there — the path `DockerBatchStrategy` reads when running the container locally.

When `DockerBatchStrategy` runs your container it injects `OUTPUT_PATH` (and `S3_OUTPUT_PATH`)
and removes the `TaskToken` from the environment, so the same image transparently writes locally
during tests and calls back via the token in production.

## Configuration

All of these are constructor arguments, so nothing is hardcoded:

| Argument | Default | Purpose |
|----------|---------|---------|
| `task_token_env_var` | `"TaskToken"` | Env var holding the Step Functions task token. |
| `output_path_env_var` | `"OUTPUT_PATH"` | Env var holding the local output file path. |
| `test_mode_env_var` | `"ENVIRONMENT"` | Env var checked for test mode. |
| `test_mode_values` | `("dev", "test")` | Values of that env var that mean "skip work". |
| `region` | resolved from `AWS_REGION` / config | Region for the `send_task_success` client. |
| `logger` | module logger | Inject your own logger. |

## Optional convenience models

`BasicJobInput`, `BasicJobOutput`, and `LastStepResults` are shipped as a common starting shape
(a step that takes a previous step's file path and a `force` flag, and returns a path +
`did_run`). They're optional — bring your own models whenever they don't fit.
