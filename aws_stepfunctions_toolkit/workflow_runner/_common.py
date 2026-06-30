"""Shared internal types and helpers for the workflow_runner subpackage."""

from __future__ import annotations

import os
from typing import TypedDict, NotRequired

import boto3
from mypy_boto3_stepfunctions.type_defs import MockInputTypeDef


TestStateInputTypeDef = TypedDict(
    "TestStateInputTypeDef",
    {
        "mock": NotRequired[MockInputTypeDef],
    },
)

TestStateInputTypeDefSlim = TypedDict(
    "TestStateInputTypeDefSlim",
    {
        "mock": NotRequired[MockInputTypeDef],
        "context": NotRequired[str | None],
    },
)


def resolve_region(region: str | None = None) -> str | None:
    """Resolve an AWS region.

    Precedence: an explicit ``region`` argument, then the ``AWS_REGION``
    environment variable, then the default region of the active boto3 session
    (``~/.aws/config`` / ``AWS_DEFAULT_REGION``). Returns ``None`` only when no
    region can be determined, in which case boto3 raises its own clear error.
    """
    return region or os.environ.get("AWS_REGION") or boto3.Session().region_name
