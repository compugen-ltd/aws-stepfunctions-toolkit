# CLI & execution history

## Generate mocks from a real execution

The fastest way to start testing an existing workflow is to capture a real past execution and
turn its per-state outputs into mock data.

```bash
sfn-toolkit generate-mock arn:aws:states:<region>:<account>:execution:MyStateMachine:exec-name
```

Options:

- `--output-dir`, `-o` — where to write (default: `data/<execution-name>/`).
- `--region`, `-r` — AWS region (otherwise resolved from `AWS_REGION` / your AWS config).

It writes three files under the output dir:

| File | Contents |
|------|----------|
| `history.json` | The complete execution history (all events). |
| `input.json` | The execution input. |
| `state_outputs.json` | Per-state mock outputs, ready to back `StaticMockResponseStrategy` entries. |

The same is available programmatically:

```python
from aws_stepfunctions_toolkit import generate_mock_data

result = generate_mock_data(
    execution_arn="arn:aws:states:...:execution:MyStateMachine:exec-name",
    output_dir="data/run1",   # optional
)
# result -> {"history": [...], "execution_input": {...}, "state_outputs": {...}, "output_dir": Path}
```

Combine this with [running a sub-range](control-flow.md#running-a-sub-range) to reproduce a
failure from the middle of a pipeline using the real captured inputs.

## Inspecting execution history

`ExecutionHistory` wraps an execution's events with convenient filters.

```python
import boto3
from aws_stepfunctions_toolkit import ExecutionHistory

client = boto3.client("stepfunctions")
history = ExecutionHistory.from_execution_arn(client, execution_arn)   # paginates for you

# Filters (each returns a list of history events):
entered   = history.filter.by_type("TaskStateEntered")
one_state = history.filter.by_state_name("ProcessData")      # events from entry to next entry
by_kind   = history.filter.by_resource_type("lambda")        # e.g. lambda / batch
by_res    = history.filter.by_resource("arn:aws:states:::batch:submitJob.sync")

# It's also directly iterable / indexable:
for event in history:
    ...
first = history[0]
n = len(history)
```

`EventFilter` (the type behind `history.filter`) is exported too if you want to filter an event
list you already have.
