# Usage: a complete worked example

This walks through running a small but realistic pipeline locally, in the spirit of the runnable
scripts under [`examples/`](https://github.com/compugen-ltd/aws-stepfunctions-toolkit/tree/master/examples).

## The workflow

`main` has four steps and calls a nested state machine:

```
example_batch_1   (Task: batch:submitJob.sync)   ─▶
example_batch_2   (Task: batch:submitJob.sync)   ─▶
child_flow        (Task: states:startExecution.sync:2)  ─▶   runs the "child" machine
example_lambda_1  (Task: lambda:invoke)          ─▶ end
```

Of these, `test_state` can run none of the task integrations directly (`.sync`,
`startExecution.sync:2`, `lambda:invoke`), so each gets a strategy.

## 1. Load the definitions

```python
import json
from pathlib import Path

DEFS = Path("examples/asl_definitions")
parent = json.loads((DEFS / "main.asl.json").read_text())
child  = json.loads((DEFS / "child.asl.json").read_text())
```

## 2. Choose how each step runs

```python
from aws_stepfunctions_toolkit import (
    DockerBatchStrategy, DockerfileImage,
    StaticMockResponseStrategy, CallableStrategy,
)

workfolder = "/data"
variables = {"workfolder": workfolder}                 # resolved into the steps' overrides
volumes = [("/host/scratch", workfolder)]              # bind-mount for the containers

mock_mapping = {
    # Real local container, built from a plain Dockerfile (no bake file needed):
    "example_batch_1": DockerBatchStrategy(
        s3_bucket="placeholder",
        image_source=DockerfileImage(context="examples/project_file/example_batch_1"),
        volumes=volumes,
        variables=variables,
    ),

    # Your own function — the simplest custom handler:
    "example_batch_2": CallableStrategy(lambda input_data: {"result": "result"}),

    # A nested-state-machine step: mock the startExecution wrapper. The "child" machine
    # is run for real by the runner (see step 3), and its output is injected back.
    "child_flow": StaticMockResponseStrategy(json.dumps({
        "ExecutionArn": "ExecutionArn",
        "StartDate": "1234567890",
        "StateMachineArn": "StateMachineArn",
        "Status": "SUCCEEDED",
    })),

    # A Lambda step: return a fixed payload.
    "example_lambda_1": StaticMockResponseStrategy(json.dumps({"result": "result"})),
}
```

## 3. Build the runner and run

```python
import os
from aws_stepfunctions_toolkit import WorkflowRunner

runner = WorkflowRunner(
    role_arn=os.environ["ROLE_ARN"],          # a role allowed to call test_state
    asl_registry={
        "main": parent,
        "child_flow": child,                  # nested machine, keyed by the step's name
    },
    mock_mapping=mock_mapping,
    variables=variables,
    region="us-east-1",                       # optional
)

initial_input = {
    "mem": {"example_batch_1": 12, "example_batch_2": 12},
    "cpu": {"example_batch_1": 4,  "example_batch_2": 4},
    "data": "somedata",
}

final_output = runner.start(initial_input)
print(final_output)
```

## 4. Swap a step's "means" without touching the ASL

The same run, with `example_batch_1` built via `docker buildx bake` instead of a Dockerfile:

```python
from aws_stepfunctions_toolkit import BakeImage

mock_mapping["example_batch_1"] = DockerBatchStrategy(
    s3_bucket="placeholder",
    image_source=BakeImage(
        bake_file="examples/docker-bake.hcl",
        target="example_batch_1",
        base_dir="examples",
    ),
    volumes=volumes,
    variables=variables,
)
```

…or, to skip Docker entirely while iterating on the flow, drop in a mock:

```python
mock_mapping["example_batch_1"] = StaticMockResponseStrategy(json.dumps({"result": "result"}))
```

## 5. Run just part of the pipeline

```python
# Start partway in, e.g. after capturing inputs from a real run (see CLI & history docs):
runner.start(initial_input, start="child_flow")

# Or run a closed sub-range and stop early:
runner.start(initial_input, start="example_batch_2", end="child_flow")
```

## As a pytest test

The shipped example is just a pytest module — wire the runner up in a test and assert on
`final_output`:

```python
def test_pipeline(tmp_path):
    runner = WorkflowRunner(role_arn=os.environ["ROLE_ARN"], asl_registry={...},
                            mock_mapping={...}, variables={"workfolder": "/data"})
    out = runner.start(initial_input)
    assert out["..."] == ...
```

Run it with `make run-example` (needs Docker, AWS creds, and `ROLE_ARN`).

## See also

- [Selecting how each step runs](strategies.md) — the full strategy + image-source catalog.
- [Control flow](control-flow.md) — subflows, Map/Parallel, recursion, start/end.
- [Container-side handler](container-handler.md) — what runs inside the batch containers.
