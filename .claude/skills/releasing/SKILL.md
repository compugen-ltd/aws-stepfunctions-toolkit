---
name: releasing
description: How this package is versioned, built, tested in CI, and published to PyPI. Use when asked to cut a release, bump/choose a version, publish to PyPI, or understand/modify the GitHub Actions CI/CD workflows. Covers tag-driven versioning (setuptools-scm), __version__, Trusted Publishing, and the ci.yml / release.yml flow.
---

# Releasing, CI/CD, and versioning

Publishing happens from **GitHub Actions**, not Jenkins — public PyPI uses **Trusted
Publishing (OIDC)**, so no API token is stored anywhere. Jenkins is not involved in the public
release.

## Versioning — the git tag is the single source of truth

- `pyproject.toml` has `dynamic = ["version"]` (no static version) and `[tool.setuptools_scm]`.
  At build time **`setuptools-scm` derives the version from the latest git tag**: tag `v0.2.0`
  -> version `0.2.0` (the leading `v` is stripped).
- Between tags / dirty tree, builds get a dev version like `0.0.1.dev60+g<sha>.dYYYYMMDD`. That
  is expected for local builds — only tagged commits produce clean release versions.
- **Choose the version yourself (SemVer):** patch `0.2.0->0.2.1` for fixes, minor `->0.3.0` for
  backward-compatible features, major `->1.0.0` for breaking changes. No tool picks this.
- **Never add a `version =` field back to `pyproject.toml`** — that reintroduces file-vs-tag
  drift. The tag is authoritative.

### `__version__` at runtime

`aws_stepfunctions_toolkit/__init__.py` exposes `__version__` by reading the **installed
package metadata** (`importlib.metadata.version("aws-stepfunctions-toolkit")`, the dist name with
hyphens), with a `PackageNotFoundError` fallback for an uninstalled source checkout. It is in
`__all__`. Don't hardcode it — it always reflects what was actually built/installed.

## Cutting a release

1. Make sure `master` is green and has everything you want to ship.
2. Decide the version (SemVer).
3. **Create a GitHub Release** with tag `vX.Y.Z` (write the release notes there).
4. Publishing the Release triggers `release.yml`, which:
   - builds sdist + wheel (`uv build`) with the version derived from the tag,
   - publishes to PyPI via Trusted Publishing (`pypa/gh-action-pypi-publish`, `id-token: write`,
     environment `pypi`),
   - uploads the built files onto the Release.

That "create a Release" click is the only manual trigger — day-to-day merges never publish.

## The workflows (`.github/workflows/`)

- **`ci.yml`** — on PRs and pushes to `master`:
  - `uv sync --dev`, then `uv run ruff check .` + `uv run ruff format --check .`,
  - **offline tests only:** `uv run pytest -m "not integration"` (the `tests/examples` suite is
    marked `integration`/`docker` and needs AWS creds + Docker + `ROLE_ARN` — see the
    `run-tests` skill),
  - a build smoke job that runs `uv build` and asserts the wheel ships `workflow_runner/*` and
    `py.typed` (packaging rule #5).
- **`release.yml`** — on `release: [published]`: build -> PyPI publish -> attach artifacts.

### Things that will bite you

- **`fetch-depth: 0`** on `actions/checkout` is required wherever the version is derived
  (build/release), so setuptools-scm can see tags + history. Without it the version is wrong.
- **Trusted Publishing must match the PyPI config:** the registered publisher pins the repo, the
  **workflow filename `release.yml`**, and the **environment `pypi`**. If you rename either, update
  the PyPI Trusted Publisher too or publishing fails with an OIDC error.
- The first PyPI upload needs the project/Trusted Publisher to exist (one-time setup on PyPI).

## Local build / inspect

```bash
uv build                       # sdist + wheel into dist/ (version from git)
uv run python -c "import aws_stepfunctions_toolkit as t; print(t.__version__)"
```

## Related

- Tests and their gating: the `run-tests` skill.
- Build/packaging rules (single public API, `packages.find`, `py.typed`): project `CLAUDE.md`.
