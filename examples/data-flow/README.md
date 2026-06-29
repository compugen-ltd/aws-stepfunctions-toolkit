# Example: how data flows between steps

This is the example to read if you're not sure **what a step receives, what it returns, and how
that becomes the next step's input.** The toolkit calls the real `test_state` API, so data flows
by exact Step Functions rules — and the shape a strategy returns matters.

The machine (JSONata) has three states:

```
Validate (Pass) ──▶ Price (Lambda, mocked) ──▶ Summarize (Pass)
```

Run it with input `{"order_id": 123, "amount": 100}` and you get:

```json
{ "order_id": 123, "total": 110.0 }
```

Below is exactly how the data gets there.

## Run it

1. **Install + run:** `uv run --python=3.13 --with aws-stepfunctions-toolkit python run.py`
   (or `pip install aws-stepfunctions-toolkit` then `python run.py`).
2. **AWS setup:** credentials + a region and a `test_state` role — see the [Setup guide](../../docs/setup.md).
3. Open [`run.py`](run.py) and set `ROLE_ARN` (`>>> **EDIT THIS** <<<`).

## Step by step: follow the data

The runner threads one value through the machine — each state's **output is the next state's
input**. Start value (`initial_input`):

```json
{ "order_id": 123, "amount": 100 }
```

### 1. `Validate` (a `Pass` state — no strategy)

Its `Output` builds a new value from the input: `{% $merge([$states.input, {'validated': true}]) %}`
— keep everything, add `validated`:

```json
{ "order_id": 123, "amount": 100, "validated": true }
```

`test_state` evaluates this on its own — no strategy needed.

### 2. `Price` (a `Lambda` task — mocked with `CallableStrategy`)

This is where a strategy plugs in:

1. **`Arguments.Payload`** = `{% $states.input %}` — what the Lambda receives.
2. **The integration runs.** `test_state` can't invoke Lambda, so your strategy supplies the
   result. `run.py` maps `Price` to:

   ```python
   CallableStrategy(lambda data: {"Payload": json.dumps({"total": round(data["amount"] * 1.1, 2)})})
   ```

   The function gets the step's input (`data`, the value from step 1) and returns the **raw result
   the Lambda integration produces** — `Payload` holding the function's return **as a JSON
   string** (`test_state` requires that, and the toolkit `$parse`s it back for you).
3. **`Output`** = `{% $merge([$states.input, {'pricing': $states.result.Payload}]) %}`. Because
   `Price` is mocked, the toolkit rewrites `$states.result.Payload` → `$parse($states.result.Payload)`
   automatically, so `pricing` becomes the parsed object.

State output:

```json
{ "order_id": 123, "amount": 100, "validated": true, "pricing": { "total": 110.0 } }
```

### 3. `Summarize` (a `Pass` state — no strategy)

Its `Output` builds a brand-new object, pulling two fields out of the accumulated value:

```json
{% { "order_id": $states.input.order_id, "total": $states.input.pricing.total } %}
```

Final output (returned by `runner.start(...)`):

```json
{ "order_id": 123, "total": 110.0 }
```

## The fields that move data (cheat sheet)

JSONata states use `$states.input` (the state input), `$states.result` (the integration result),
and `$states.context` (execution metadata), with:

| Field | What it does |
|-------|--------------|
| `Arguments` | Build the payload the integration receives. |
| *(integration)* | Produces the **raw result** in `$states.result` — here supplied by your strategy. |
| `Output` | Build the state's output (becomes the next state's input). |

(JSONPath machines use `InputPath` / `Parameters` / `ResultSelector` / `ResultPath` / `OutputPath`
instead — same idea. Note: a mocked `lambda:invoke` needs `Payload` as a string, and only JSONata
`Output` gets the automatic `$parse` rewrite — so mock Lambda steps with JSONata.)

## What a strategy must return

A strategy supplies the **raw result** the integration would return, *before* `Output` runs — so
match the real shape:

| Integration | Return this shape |
|-------------|-------------------|
| `lambda:invoke` | `{"Payload": "<function return as a JSON string>"}` (as `Price` does here). |
| `batch:submitJob.sync` | the job's result object (e.g. what your container writes to `OUTPUT_PATH`). |
| `states:startExecution.sync:2` | the execution wrapper — handled for you by `StandardFlowStrategy`. |
