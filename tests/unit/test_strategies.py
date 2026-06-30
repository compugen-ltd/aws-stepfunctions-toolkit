"""Offline unit tests for the strategies that don't call test_state."""

import json

from aws_stepfunctions_toolkit import (
    CallableStrategy,
    StaticMockResponseStrategy,
    DockerBatchStrategy,
)


def test_callable_strategy_json_encodes_dict_result():
    out = CallableStrategy(lambda data: {"echo": data, "ok": True}).execute(
        "S", {}, {"x": 1}, orchestrator=None, context="{}"
    )
    assert out["mock"]["result"] == json.dumps({"echo": {"x": 1}, "ok": True})
    assert out["context"] == "{}"


def test_callable_strategy_passes_through_a_string_result():
    out = CallableStrategy(lambda data: '{"already": "json"}').execute(
        "S", {}, {}, orchestrator=None
    )
    assert out["mock"]["result"] == '{"already": "json"}'


def test_static_mock_returns_the_given_result_verbatim():
    out = StaticMockResponseStrategy('{"Payload": "x"}').execute(
        "S", {}, {}, orchestrator=None
    )
    assert out["mock"]["result"] == '{"Payload": "x"}'


def test_docker_batch_rejects_non_image_source():
    import pytest

    with pytest.raises(TypeError):
        DockerBatchStrategy(s3_bucket="b", image_source="not-a-source")
