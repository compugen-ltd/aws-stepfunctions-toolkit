# Example: how data flows between steps

This is the example to read if you're not sure **what a step receives, what it returns, and how
that becomes the next step's input.** The toolkit calls the real `test_state` API, so data flows
by exact Step Functions rules — and the shape a strategy returns matters.

The machine has three states:

```
Validate (Pass) ──▶ Price (Lambda, mocked) ──▶ Summarize (Pass)
```

Run it with input `{"order_id": 123, "amount": 100}` and you get:

```json
{ "order_id": 123, "total": 110.0 }
```

Below is exactly how the data gets there.

## Run it

1. **Install:** `pip install aws-stepfunctions-toolkit`.
2. **AWS setup:** credentials + a region and a `test_state` role — see the [Setup guide](../../docs/setup.md).
3. Open [`run.py`](run.py) and set `ROLE_ARN` (`>>> **EDIT THIS** <<<`).
4. **Run:** `python run.py`.

## Step by step: follow the data

The runner threads one value through the machine — each state's **output is the next state's
input**. Start value (`initial_input`):

```json
{ "order_id": 123, "amount": 100 }
```

### 1. `Validate` (a `Pass` state — no strategy)

A `Pass` state with `"Result": true` and `"ResultPath": "$.validated"`. `ResultPath` says *where
to graft this state's result into the incoming data*. So it adds a `validated` key and passes
everything else through:

```json
{ "order_id": 123, "amount": 100, "validated": true }
```

`test_state` evaluates this on its own — no strategy needed.

### 2. `Price` (a `Lambda` task — mocked with `CallableStrategy`)

This is where a strategy plugs in. The flow within the state:

1. **`Parameters`** builds the Lambda input: `"Payload.$": "$"` → the whole current value.
2. **The integration runs.** `test_state` can't invoke Lambda, so your strategy supplies the
   result. `run.py` maps `Price` to:

   ```python
   CallableStrategy(lambda data: {"Payload": {"total": round(data["amount"] * 1.1, 2)}})
   ```

   The function receives the step's input (`data`, the value from step 1) and returns the **raw
   result the Lambda integration would** — `{"Payload": {"total": 110.0}}`. (Returning the shape
   the real service returns is the key idea — see the table at the bottom.)
3. **`ResultSelector`** reshapes that raw result: `"total.$": "$.Payload.total"` → `{"total": 110.0}`.
4. **`ResultPath`** grafts it in at `$.pricing`.

State output:

```json
{ "order_id": 123, "amount": 100, "validated": true, "pricing": { "total": 110.0 } }
```

### 3. `Summarize` (a `Pass` state — no strategy)

`Parameters` builds a brand-new object, pulling two fields out of the accumulated value:

```json
{ "order_id.$": "$.order_id", "total.$": "$.pricing.total" }
```

Final output (returned by `runner.start(...)`):

```json
{ "order_id": 123, "total": 110.0 }
```

## The fields that move data (cheat sheet)

Within one state, data flows: `input → InputPath → Parameters → [integration result] →
ResultSelector → ResultPath → OutputPath → output`.

| Field | What it does |
|-------|--------------|
| `InputPath` | Select a slice of the state input to work with. |
| `Parameters` | Build the payload the integration receives (`.$` = a path/expression). |
| *(integration)* | Produces the **raw result** — here supplied by your strategy. |
| `ResultSelector` | Reshape the raw result. |
| `ResultPath` | Where to graft the result into the input (omit fields → replace; `$.x` → add). |
| `OutputPath` | Final slice to pass on as the state output. |

(JSONata machines use `Arguments` + `Output` with `$states.input` / `$states.result` instead —
same idea.)

## What a strategy must return

A strategy supplies the **raw result** the integration would return, *before* `ResultSelector`/
`Output` run — so match the real shape:

| Integration | Return this shape |
|-------------|-------------------|
| `lambda:invoke` | `{"Payload": <function return>}` (as `Price` does here). |
| `batch:submitJob.sync` | the job's result object (e.g. what your container writes to `OUTPUT_PATH`). |
| `states:startExecution.sync:2` | the execution wrapper — handled for you by `StandardFlowStrategy`. |

If `Price` returned a bare `{"total": 110.0}`, the `ResultSelector` (`$.Payload.total`) would find
nothing — that's the most common data-flow mistake.
