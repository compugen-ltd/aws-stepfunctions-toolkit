.PHONY: build build-publish version-bump publish

SHELL=/bin/bash

UV_BIN := $(shell uv tool dir --bin)
export PATH := $(UV_BIN):$(PATH)

build:
	rm -rf build dist
	uv build

build-publish: build
	rm -rf build dist
	uv build
	@$(MAKE) publish

version-bump:
	uv version --bump patch

publish:
	uv publish --index aws

