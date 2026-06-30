.PHONY: build build-publish publish tag test test-examples run-example

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
