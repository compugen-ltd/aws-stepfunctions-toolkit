# CLAUDE.md — aws-stepfunctions-toolkit

Project-specific guidance for this repo. This is a **public, open-source** Python package — keep
everything generic and free of org-specific values.

## What this is

A toolkit to run AWS Step Functions state machines **end-to-end locally**. `WorkflowRunner` walks
a real ASL definition state-by-state, calls the AWS `test_state` API for the engine-side logic
(InputPath/Parameters/Arguments/ResultSelector/Output + next-state), and uses pluggable
**strategies** to supply the result of steps `test_state` can't run (`.sync` Batch jobs,
`startExecution.sync:2`, `.waitForTaskToken`) — typically by building/running that step's
container locally with Docker.

Motivation: born from a pipeline dominated by `batch:submitJob.sync` steps, where the Test State
API can't run those steps and a full AWS run was too slow to iterate on.

## Architecture (where things live)

```
aws_stepfunctions_toolkit/
  __init__.py            # THE public API — re-exports everything + __all__
  history.py             # ExecutionHistory + EventFilter (read execution history)
  testing.py             # generate_mock_data() — mocks from a real execution
  cli.py                 # `sfn-toolkit generate-mock`
  batch_job_interface.py # BatchJobInterface — base for code running INSIDE job containers
  workflow_runner/
    workflow_runner.py   # WorkflowRunner orchestrator (the run loop)
    strategies.py        # StateExecutionStrategy + concrete strategies
    image_sources.py     # ImageSource: PrebuiltImage / DockerfileImage / BakeImage (+ ECR/codeartifact helpers)
    models.py            # pydantic models (ExecutionContext, StartExecutionResult, AslDefinition, DockerBatchConfig)
    _common.py           # internal: shared TypedDicts + resolve_region()
```

## Hard rules

1. **Single public API.** Everything users need is re-exported from the top-level
   `aws_stepfunctions_toolkit/__init__.py` with a curated `__all__`. In docs/examples/tests,
   import from the package root (`from aws_stepfunctions_toolkit import WorkflowRunner`), never
   deep paths. When you add a public symbol, add it to **both** `workflow_runner/__init__.py`
   (if it lives there) and the top-level `__init__.py` + `__all__`. Prefix true internals with
   `_` (e.g. `_common.py`).

2. **No org-specific values — ever.** No account IDs, bucket names, AppConfig
   app/env/profile identifiers, role/queue/JD ARNs, dataset names, or `/Rnd/`-style paths in
   shipped code. Make them constructor arguments. Region must go through
   `aws_stepfunctions_toolkit.workflow_runner._common.resolve_region` (explicit arg → `AWS_REGION`
   → boto3 session); never hardcode `us-east-1` for a client. The only `us-east-1` literals
   allowed are the inert placeholder ARNs in `models.py:StartExecutionResult` (account
   `000000000000`) and example ASL files (fake accounts). Sweep before committing:
   `rg -n "000000000000|/Rnd/|royassis|us-east-1" aws_stepfunctions_toolkit`.

3. **Don't hardcode a bake file.** Docker images come from a pluggable `ImageSource`.
   `DockerfileImage` (plain `docker build`) is the easy default; `BakeImage` is one option, not a
   requirement. `DockerBatchStrategy` takes `image_source=` and contains no build logic.

4. **Extension points stay open.** Users define their own handler via `CallableStrategy(handler)`
   or by subclassing `StateExecutionStrategy`; their own image build via subclassing
   `ImageSource` (implement `ensure_image() -> str`); their own container contract via
   `BatchJobInterface[InputT, OutputT]` with their own pydantic models. Don't bake assumptions
   about input/output shape into these bases.

5. **Packaging must include subpackages.** `pyproject.toml` uses
   `[tool.setuptools.packages.find] include = ["aws_stepfunctions_toolkit*"]`. Do NOT revert to a
   hardcoded `packages = ["aws_stepfunctions_toolkit"]` — that drops the `workflow_runner`
   subpackage (the whole engine) from the wheel. After packaging changes, verify the built wheel
   contains `workflow_runner/*.py` and `py.typed`.

6. **`models.py` must NOT use `from __future__ import annotations`** — it breaks Pydantic's nested
   model field resolution. (Other modules use it fine.)

7. **Ignore `.kiro/`.** The `.kiro/` folder is kept for historical reasons only — it is not part
   of the package and may be removed entirely. Don't read it for current guidance, don't update
   it, and don't treat its steering/knowledge files as authoritative. This `CLAUDE.md` is the
   source of truth for project rules.

## Conventions

- Python **3.13**; modern typing (`dict`/`list`, `X | None`), full param + return annotations.
- `pathlib.Path` for filesystem paths; no `os.path` / string concatenation.
- Constants in `UPPER_SNAKE_CASE` near the top of the module.
- Run things with `uv run ...` (e.g. `uv run pytest`, `uv build`).

## pre-commit & secret scanning

This repo uses **pre-commit** (`.pre-commit-config.yaml`) — install the hooks once with
`uv run pre-commit install`; they run on commit (and can be run on demand with
`uv run pre-commit run --all-files`). Hooks include `detect-secrets`, `gitleaks`,
`detect-private-key`, and the standard hygiene hooks (large-files, merge-conflict, yaml,
end-of-file-fixer, trailing-whitespace).

- `detect-secrets` runs against **`.secrets.baseline`**. Real secrets must never be committed;
  if `detect-secrets` flags a new finding, fix it (don't commit the secret). Only when a finding
  is a verified false positive, audit and refresh the baseline with
  `uv run detect-secrets scan --baseline .secrets.baseline` (review the diff before committing).
- Real env values live in `data.env`, which is gitignored (`*.env` with `!example.env`); commit
  only `example.env` with placeholders.

## Container contract (DockerBatchStrategy ↔ your image)

The strategy mounts a writable temp dir at `/tmp`, injects `OUTPUT_PATH` (=`/tmp/output.json`)
and `S3_OUTPUT_PATH`, and removes `TaskToken` from the env before running. Your container writes
its result JSON to `/tmp/output.json`. `BatchJobInterface.send_response` mirrors this: task token
present → `send_task_success`; else write to `OUTPUT_PATH`.

## Testing

- The example tests (`examples/run_tests.py`, `make run-example`) make **real** `test_state` API
  calls and build/run Docker containers — they need Docker running, AWS credentials, and a
  `ROLE_ARN` env var (a role allowed to call `test_state`).
- Offline, you can only verify the pure-Python pieces (strategy result encoding, `ImageSource`
  type guard, `BatchJobInterface` skip/`OUTPUT_PATH`, `resolve_region`) — `runner.start` always
  hits AWS.
- Sanity after API/packaging changes:
  `uv run python -c "import aws_stepfunctions_toolkit as t; print(len(t.__all__))"` and a build.

## Docs

User-facing docs live in `README.md` (concise) + `docs/*.md` (how-it-works, usage, strategies,
control-flow, container-handler, cli-and-history). Keep docs in sync with actual signatures —
the previous README documented an API that didn't exist.

## Third-party notices (legal requirement)

Legal requires a `ThirdPartyNotices.txt` covering our dependencies' licenses/copyrights. It is
**generated, not hand-edited** — regenerate it whenever dependencies change.

- Generate with `scripts/generate_third_party_notices.sh`. It compiles `pyproject.toml` →
  `requirements.txt`, then runs the OSS Review Toolkit (`ghcr.io/oss-review-toolkit/ort:latest`)
  analyze → scan → report to produce the notice file, and copies the result to
  `ThirdPartyNotices.txt`. Needs Docker.
- `ossconfig.yaml` is the ORT config consumed by that container (mounted as
  `~/.ort/config/config.yml`) — it configures the ScanCode scanner (copyright/license extraction)
  and the local file-based scan-result cache. Edit it to change scan options, not the notice
  content directly.
- The script cleans up its scratch (`requirements.txt`, `.ort-temp/`), which are gitignored.
  Don't hand-edit `ThirdPartyNotices.txt`; re-run the script.
