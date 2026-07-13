# Control flow: subflows, Map, Parallel, recursion, start/end

States you don't put in `mock_mapping` are handled by the built-in `StandardFlowStrategy`, which
understands the composite states and recurses into them. This page covers how that works and how
to control it.

## Subflows (nested state machines)

A `Task` with resource `arn:aws:states:::states:startExecution.sync:2` starts another state
machine. The toolkit runs that nested machine **in the same local loop** and injects its output
back into the parent step — so a multi-machine pipeline runs end-to-end locally.

Register each nested machine in `asl_registry` **keyed by the name of the state that starts it**:

```python
runner = WorkflowRunner(
    asl_registry={
        "main": {**parent_definition, "ROLE_ARN": parent_role_arn},
        # the parent has a startExecution task state named "child_flow":
        "child_flow": {**child_definition, "ROLE_ARN": child_role_arn},
    },
    mock_mapping=mock_mapping,
)
```

If a `startExecution` step's name isn't found in the registry, you get a clear error listing the
available keys.

### Per-machine execution roles

Each registry entry carries its **own** `ROLE_ARN` — the execution role that machine's states run
under via `test_state`. As execution crosses a nested `startExecution` boundary the runner switches
the active role to the sub-machine's role (and restores the parent's afterward), matching real AWS
where a parent and its sub-machine have distinct roles. Giving the child a narrower role surfaces
per-role IAM scoping bugs (e.g. a missing permission on the child role) that a single shared role
would hide. `ROLE_ARN` is required on every entry — there's no shared-role fallback.

## Map states

For a `Map` state, `StandardFlowStrategy` runs the `ItemProcessor` once per item. By default the
items are the state's input when it's a list, otherwise `input["items"]`.

When the items live somewhere else in the input, subclass `AbstractMockMapResponseStrategy` and
implement `get_items`:

```python
from aws_stepfunctions_toolkit import AbstractMockMapResponseStrategy

class SamplesMap(AbstractMockMapResponseStrategy):
    def get_items(self, input_data):
        return input_data["samples"]["Payload"]["body"]

mock_mapping = {"Map - Samples": SamplesMap(), ...}
```

The strategy uses `test_state` to apply the Map's ItemSelector to each item, then runs each
through the ItemProcessor.

## Parallel states

For a `Parallel` state, each branch is run through the local loop and the results are collected
into a list, mirroring Step Functions' output shape.

## Recursion and depth

Subflows, Maps and Parallels can nest to any depth — each composite state recurses back into the
same `run_sub_machine` loop. As it descends, the runner tracks a **parent path** so steps deep
inside the tree can be addressed precisely.

### Hierarchical keys

Strategy lookup tries the most specific key first, then the bare name:

1. `"<parent_path>/<state_name>"` — e.g. `"child_flow/example_batch_2"`
2. `"<state_name>"`

So a plain `"example_batch_2"` key applies to that state wherever it appears, while
`"child_flow/example_batch_2"` targets only the occurrence inside the `child_flow` subflow. The
parent path segments are the names of the enclosing subflow / Map / Parallel states.

## Running a sub-range

`runner.start` runs the whole `"main"` machine by default, but you can run just part of it:

```python
runner.start(initial_input, start="Parallel")        # begin at a specific state
runner.start(initial_input, start="A", end="C")      # stop after state "C"
```

- `start` — the state to begin at (instead of the definition's `StartAt`).
- `end` — the state after which to stop (its output is returned).

This is handy for reproducing a failure from the middle of a long pipeline without re-running the
earlier steps — pair it with mocked inputs captured from a real run (see
[CLI & history](cli-and-history.md)).
