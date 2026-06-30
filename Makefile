.PHONY: build build-publish publish tag test test-examples run-example docs docs-serve docs-clean

SHELL=/bin/bash

UV_BIN := $(shell uv tool dir --bin)
export PATH := $(UV_BIN):$(PATH)

build:
	rm -rf build dist
	uv build

# Tag the current HEAD as a release. The tag IS the version (setuptools-scm
# derives it), so there is no version field to bump. Usage: make tag VERSION=0.2.0
tag:
	@test -n "$(VERSION)" || { echo "Usage: make tag VERSION=0.2.0"; exit 1; }
	git tag -a v$(VERSION) -m "Release v$(VERSION)"

# Publish to PyPI. Token via UV_PUBLISH_TOKEN (Trusted Publishing is CI-only).
# IRREVERSIBLE: a PyPI version can't be re-uploaded or truly deleted. Prefer the
# CI release (publish a GitHub Release) or the `/release` command / release-local
# skill, which run pre-flight checks first.
publish:
	uv publish

build-publish: build publish

run-example:
	uv run python examples/docker-batch/run.py

test:
	uv run pytest tests/unit -n auto

test-examples:
	uv run pytest tests/examples -n auto

# Build the documentation site (Sphinx + MyST). -W = warnings are errors, same
# as CI and Read the Docs. Needs the docs extra: `uv sync --extra docs`.
docs:
	uv run --extra docs sphinx-build -W -b html docs docs/_build/html

# Live-reloading local preview at http://127.0.0.1:8000 (requires sphinx-autobuild).
docs-serve:
	uv run --extra docs --with sphinx-autobuild sphinx-autobuild docs docs/_build/html

docs-clean:
	rm -rf docs/_build
