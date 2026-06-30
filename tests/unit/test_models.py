"""Offline unit tests for the pydantic models."""

import json

import pytest
from pydantic import ValidationError

from aws_stepfunctions_toolkit import (
    StartExecutionResult,
    ExecutionContext,
    AslDefinition,
)


def test_start_execution_result_output_defaults_to_a_string():
    # test_state rejects a null Output ("Field 'Output' must be a string").
    result = StartExecutionResult(Input="{}").model_dump()
    assert isinstance(result["Output"], str)
    assert result["Output"] == "{}"


def test_start_execution_result_roundtrips_as_json():
    dumped = StartExecutionResult(Input=json.dumps({"a": 1})).model_dump_json()
    parsed = json.loads(dumped)
    assert isinstance(parsed["Output"], str)
    assert parsed["Status"] == "SUCCEEDED"


def test_execution_context_with_input_and_token():
    ctx = ExecutionContext().with_input({"x": 1})
    assert ctx.Execution.Input == {"x": 1}
    assert ctx.Task is None
    ctx = ctx.with_task_token()
    assert ctx.Task is not None
    # exclude_none drops Task when absent
    assert "Task" not in json.loads(
        ExecutionContext().with_input({}).model_dump_json(exclude_none=True)
    )


def test_asl_definition_requires_startat_and_states():
    AslDefinition.model_validate(
        {"StartAt": "A", "States": {"A": {"Type": "Pass", "End": True}}}
    )
    with pytest.raises(ValidationError):
        AslDefinition.model_validate({"States": {}})  # missing StartAt
