---
description: Cut a release manually and locally — pre-flight checks, tag, build, verify, then publish to PyPI (with confirmation) and push the tag.
argument-hint: <version, e.g. 0.2.0>
---
Perform a MANUAL, LOCAL release of this package to PyPI, following the `release-local` skill.
Target version: `$ARGUMENTS` (if empty, ask me for it — SemVer, no leading `v`).

Do these in order and STOP on the first failure. Use terse progress pings.

1. **Pre-flight** (abort if any fails, report what failed):
   - On `master`, working tree clean, and up to date with `origin/master`.
   - `uv run pytest -m "not integration"` passes.
   - `uv run ruff check .` and `uv run ruff format --check .` pass.
   - `uv run pre-commit run gitleaks --all-files` passes (guards against a stray account ID).

2. **Confirm the version with me**, then tag the current clean HEAD (annotated):
   `git tag -a v$ARGUMENTS -m "Release v$ARGUMENTS"`. setuptools-scm derives the package version
   from this tag — the tag is the source of truth.

3. **Build + verify:** `rm -rf dist build && uv build`. Confirm the built filenames are exactly
   `...-$ARGUMENTS-...` with NO `.devN` / `+dirty` suffix (if present, the tree wasn't clean or
   the tag isn't on HEAD — fix before continuing), and the wheel contains `workflow_runner/*.py`
   and `py.typed`.

4. **Publish (IRREVERSIBLE — get my explicit OK first):** a PyPI version can never be re-uploaded
   or truly deleted. On my confirmation, publish with a token:
   `uv publish` (token via `UV_PUBLISH_TOKEN` or `--token`; PyPI is the default publish URL).
   Offer a TestPyPI dry-run first if I want one.

5. **Push the tag:** `git push origin v$ARGUMENTS`.

6. Do **NOT** create a GitHub Release that would trigger `release.yml` to publish the same version
   again — PyPI rejects duplicate uploads. See the skill's caveat for the options.

Finish with a summary: what was published (name + version + index) and the pushed tag.
