---
description: Run the project's tests (offline unit suite, plus example integration suite when ROLE_ARN is set)
---
Run the project's test suite and report a concise pass/fail summary.

1. Run the offline unit tests: `make test` (= `uv run pytest tests/unit -n auto`).
2. If the `ROLE_ARN` environment variable is set, also run the example integration tests:
   `make test-examples` (= `uv run pytest tests/examples -n auto`). Otherwise note they were
   skipped — they need `ROLE_ARN` + Docker (see `docs/setup.md`); the offline completeness guard
   still runs.

On failure, show the failing test names and the relevant output. Don't modify code unless asked.
