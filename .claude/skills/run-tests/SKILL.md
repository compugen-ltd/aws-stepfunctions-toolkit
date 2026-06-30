---
name: run-tests
description: Run this project's test suite — the offline unit tests and the example integration tests. Use when asked to run tests, verify the build, or check that the examples still work. Covers the make targets, parallel execution via pytest-xdist, and the ROLE_ARN/Docker gating.
---

# Running the tests

Two layers, both run in parallel via pytest-xdist (`-n auto`).

## Unit tests — offline, no AWS/Docker (run these for any change)

```bash
make test          # = uv run pytest tests/unit -n auto
```

Fast, deterministic, CI-friendly. They cover the pure logic: strategy result encoding, the
`ImageSource` type guard, `resolve_region`, `BatchJobInterface` skip/`OUTPUT_PATH`, models, and
the runner's rewrites (`alter_mock_step`, `_format_definitions`, `has_token`,
`_collect_all_state_names`, the context `State.Name`).

## Example integration tests — real `test_state`

```bash
make test-examples # = uv run pytest tests/examples -n auto
```

Each runs an example end-to-end against the real `test_state` API. Gating:

- **Needs `ROLE_ARN`** (an IAM role allowed to call `states:TestState`). Locally it's read from
  the gitignored `data.env` at the repo root (the test conftest loads it via `python-dotenv`), so
  `make test-examples` just works without exporting anything. In CI there's no `data.env`, so
  these auto-skip. An exported `ROLE_ARN` still wins.
- Docker examples (`docker-batch/*`, parametrized over `dockerfile` + `bake`) skip unless a
  Docker daemon is reachable.
- `mock-generation` skips unless `EXECUTION_ARN` is set; `advanced-deployed` skips unless
  `STATE_MACHINE_ARN` / `FUNCTION_ARN` / `SFN_ROLE_ARN` are set (add any of these to `data.env`
  to run them locally too).
- The **completeness guard** `test_all_example_scripts_are_covered` runs offline regardless and
  fails if any `examples/*/run*.py` isn't covered by a test.

To exercise everything end-to-end, just ensure `data.env` has a valid `ROLE_ARN` (see
[`docs/setup.md`](../../../docs/setup.md) for AWS credentials and creating the `test_state` role),
then:

```bash
make test-examples
```

Run a single test with `uv run pytest tests/unit/test_runner_logic.py -k <name>`.
