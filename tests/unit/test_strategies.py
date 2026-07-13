"""Offline unit tests for the strategies that don't call test_state."""

import json

import pytest

from aws_stepfunctions_toolkit import (
    CallableStrategy,
    StaticMockResponseStrategy,
    DockerBatchStrategy,
    DockerLambdaStrategy,
    LocalLambdaImageStrategy,
    PrebuiltImage,
    get_lambda_payload,
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
    with pytest.raises(TypeError):
        DockerBatchStrategy(s3_bucket="b", image_source="not-a-source")


def test_docker_lambda_rejects_non_image_source():
    with pytest.raises(TypeError):
        DockerLambdaStrategy(image_source="not-a-source")


def test_local_lambda_image_is_alias_of_docker_lambda():
    assert LocalLambdaImageStrategy is DockerLambdaStrategy


class _FakeSFN:
    def __init__(self, after_arguments):
        self._after = after_arguments
        self.last_kwargs = None

    def test_state(self, **kw):
        self.last_kwargs = kw
        return {"inspectionData": {"afterArguments": json.dumps(self._after)}}


def test_get_lambda_payload_extracts_payload_from_trace():
    fake = _FakeSFN({"FunctionName": "fn", "Payload": {"number": 21}})
    payload = get_lambda_payload(fake, {"Resource": "..."}, "role", {}, {"n": 1}, "{}")
    assert payload == {"number": 21}
    assert fake.last_kwargs["roleArn"] == "role"
    assert fake.last_kwargs["inspectionLevel"] == "TRACE"


def test_get_lambda_payload_requires_a_payload_field():
    fake = _FakeSFN({"FunctionName": "fn"})  # no Payload
    with pytest.raises(RuntimeError, match="Payload"):
        get_lambda_payload(fake, {}, "role", {}, {}, "{}")


class _FakeOrchestrator:
    active_role_arn = "arn:aws:iam::000000000000:role/dummy"

    def __init__(self):
        self.client = _FakeSFN({"Payload": {"number": 21}})


def test_docker_lambda_wraps_handler_output_as_lambda_invoke_result(monkeypatch):
    strat = DockerLambdaStrategy(image_source=PrebuiltImage("some-image:latest"))
    monkeypatch.setattr(strat.image_source, "ensure_image", lambda: "some-image:latest")
    # Skip Docker entirely: the "handler" just doubles the number.
    monkeypatch.setattr(
        strat,
        "_invoke_via_rie",
        lambda image, payload, envs: {"doubled": payload["number"] * 2},
    )
    out = strat.execute("L", {}, {"n": 1}, _FakeOrchestrator(), context="{}")

    result = json.loads(out["mock"]["result"])
    assert result["StatusCode"] == 200
    # Payload is a JSON *string* (test_state requires it); it $parses back to the handler output.
    assert json.loads(result["Payload"]) == {"doubled": 42}
    assert out["context"] == "{}"
