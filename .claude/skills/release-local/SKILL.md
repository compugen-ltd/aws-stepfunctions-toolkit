---
name: release-local
description: Cut a release by hand from a local machine — tag, build, and publish to PyPI without going through GitHub Actions. Use for the first release, when CI is unavailable, or to publish from a dev box. Covers token auth (vs CI's Trusted Publishing), the tag-as-version rule, and how to avoid a double-publish with release.yml. The `/release` command automates this.
---

# Local manual release

The **normal** path is automated: create a GitHub Release → `release.yml` builds and publishes to
PyPI via Trusted Publishing (see the `releasing` skill). This skill is the **manual, local**
fallback — build and publish straight from your machine. The `/release <version>` command runs it.

## The one auth difference vs CI

CI publishes with **Trusted Publishing (OIDC)** — no token. **Locally that is not available**, so
a local publish uses a **PyPI API token**:

- `uv publish` reads `UV_PUBLISH_TOKEN` (or `--token`). PyPI is the default publish URL.
- Keep the token out of git — put it in the gitignored `data.env` (`UV_PUBLISH_TOKEN=pypi-...`) or
  your keyring. Never commit it; never paste it into a tracked file.

## Procedure

1. **Pre-flight** — abort on any failure:
   - on `master`, clean working tree, up to date with `origin/master`;
   - `uv run pytest -m "not integration"` (offline suite) passes;
   - `uv run ruff check .` and `uv run ruff format --check .` pass;
   - `uv run pre-commit run gitleaks --all-files` passes (account-ID guard).
2. **Pick the version** (SemVer: patch/minor/major — your call) and **tag the clean HEAD**:
   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   ```
   The tag IS the version — setuptools-scm reads it at build time.
3. **Build + verify:**
   ```bash
   rm -rf dist build && uv build
   ls dist/                      # expect aws_stepfunctions_toolkit-0.2.0-...
   ```
   The filename must be exactly the version with **no `.devN` / `+dirty` suffix**. A suffix means
   the tree was dirty or the tag isn't on HEAD — fix that, the version would be wrong. Confirm the
   wheel ships `workflow_runner/*.py` + `py.typed` (packaging rule #5).
4. **(Optional) TestPyPI dry-run:**
   ```bash
   uv publish --publish-url https://test.pypi.org/legacy/ --token <testpypi-token>
   ```
5. **Publish to PyPI — IRREVERSIBLE:** a version can never be re-uploaded or truly deleted, so be
   sure first.
   ```bash
   uv publish                    # uses UV_PUBLISH_TOKEN
   ```
6. **Push the tag:** `git push origin v0.2.0`.

## Caveat: don't double-publish with `release.yml`

`release.yml` publishes when a **GitHub Release is published**. If you release locally AND then
create a GitHub Release for the same tag, CI will try to upload the same version and **PyPI rejects
duplicates** (the CI job fails). Pick one:

- **Local only:** just push the tag; skip the GitHub Release (or create it as notes-only/draft).
- **CI only:** don't publish locally — create the Release and let CI do it (the recommended path).
- If you want both a local publish *and* a GitHub Release, add `with: { skip-existing: true }` to
  the `pypa/gh-action-pypi-publish` step so the CI re-publish no-ops.

## Legacy Makefile targets (do not use as-is)

The `Makefile` predates tag-based versioning + PyPI:

- `make version-bump` runs `uv version --bump patch`, which **writes a static version** — that
  conflicts with `dynamic = ["version"]`. Don't bump a version in a file; **tag instead**.
- `make publish` runs `uv publish --index aws`, the **old private CodeArtifact** path. For the
  public release, publish to **PyPI** (default), not `--index aws`.

Use the tag → `uv build` → `uv publish` flow above. (Offer to update/retire those Makefile targets
if they're getting in the way.)

## Related

- `releasing` — versioning model, `__version__`, and the CI/CD (`ci.yml` / `release.yml`) flow.
- `run-tests` — the test suites and their gating.
