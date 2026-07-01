# How it works

## The problem

A Step Functions development loop usually looks like: deploy the state machine to AWS, start an
execution, read the execution history, find what broke, change the definition or a Lambda/Batch
job, redeploy, run again. Every iteration costs minutes and money.

AWS's [`test_state`](https://docs.aws.amazon.com/step-functions/latest/apireference/API_TestState.html)
API helps for a *single* state: given a state definition and an input, it evaluates the state's
data flow (InputPath / Parameters / Arguments / ResultSelector / Output) and tells you the next
state — without deploying anything. But it has two limits:

1. It runs **one state at a time** — it doesn't walk a whole machine.
2. It **cannot execute** service integrations such as `.sync` (e.g.
   `arn:aws:states:::batch:submitJob.sync`), nested `startExecution.sync:2`, or
   `.waitForTaskToken` — the exact steps that are slowest to iterate on.

This package grew out of a data pipeline built almost entirely from `batch:submitJob.sync`
steps: every one needed a hand-rolled workaround to test, and running the real state machine on
AWS to validate a change was far too slow. The aim was a quick way to run the **whole** pipeline
end-to-end locally, with the Batch steps actually executing in local containers.

## The approach

![Annotated Step Functions workflow showing how the toolkit runs each state type: test_state for engine logic, a strategy (e.g. local Docker) for .sync steps, and recursion for nested subflows](overview.svg)

*The real Step Functions console graph of the [docker-batch](https://github.com/compugen-ltd/aws-stepfunctions-toolkit/tree/master/examples/docker-batch) example,
annotated to show how each state is handled. Editable source:
[`overview.drawio`](overview.drawio) (the console graph is embedded; edit the annotation layer in
[draw.io](https://app.diagrams.net) and re-export `overview.svg`).*

`WorkflowRunner` walks your real ASL definition state-by-state. For each state it:

1. Picks a **strategy** that supplies the state's *result* (see
   [Selecting how each step runs](strategies.md)). States you don't map are handled
   automatically.
2. Calls `test_state` with your definition + that result, so **AWS still does the engine work**
   — the data transforms and the next-state transition. You get faithful behavior, not a
   reimplementation of the States Language.
3. Feeds the resulting output into the next state, and repeats until the machine ends.

```
          ┌───────────────────────── WorkflowRunner.run loop ─────────────────────────┐
input ──▶ │  pick strategy ─▶ strategy.execute() ─▶ result                             │
          │                                   │                                        │
          │                                   ▼                                        │
          │   test_state(definition, input, **result)  ◀── AWS evaluates data flow     │
          │                                   │           + returns nextState          │
          │                                   ▼                                        │
          │            output  ──────────────────────────▶ next state ─┐               │
          └────────────────────────────────────────────────────────────┘               │
                                            (loop)                                       
```

For a step the API can't run — say a `batch:submitJob.sync` task — a strategy like
`DockerBatchStrategy` builds and runs that step's container **locally** and returns its output;
`test_state` then applies the state's `Output`/ResultSelector exactly as it would in production.

## What you provide

- **`role_arn`** — an IAM role/credentials allowed to call `test_state`.
- **`asl_registry`** — your ASL definition(s), keyed by name; the entry point must be `"main"`.
  Nested state machines are registered too (see [Control flow](control-flow.md)).
- **`mock_mapping`** — `{state_name: strategy}` choosing how the steps that need help run.
- Optional **`variables`** (Step Functions context variables), an
  **`input_validation_function`**, and a **`region`** (otherwise resolved from `AWS_REGION` /
  your AWS config).

Then `runner.start(initial_input)` returns the final output. See
[Getting started / usage](usage.md) for a complete worked example.
