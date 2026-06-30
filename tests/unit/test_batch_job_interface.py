"""Offline unit tests for the container-side BatchJobInterface."""

import json

from pydantic import BaseModel

from aws_stepfunctions_toolkit import BatchJobInterface


class In(BaseModel):
    order_id: int


class Out(BaseModel):
    order_id: int
    status: str


class _Job(BatchJobInterface[In, Out]):
    input_model = In
    output_model = Out

    def should_run(self, i: In) -> bool:
        return i.order_id > 0

    def run(self, i: In) -> Out:
        return Out(order_id=i.order_id, status="processed")

    def create_skip_output(self, i: In) -> Out:
        return Out(order_id=i.order_id, status="skipped")


def _run_job(raw_input, env, tmp_path):
    op = tmp_path / "out.json"
    env = {**env, "OUTPUT_PATH": str(op)}
    # apply env
    import os

    for k, v in env.items():
        os.environ[k] = v
    os.environ.pop("TaskToken", None)
    try:
        out = _Job().execute(raw_input)
    finally:
        for k in env:
            os.environ.pop(k, None)
    return out, json.loads(op.read_text())


def test_runs_and_writes_output_path(tmp_path):
    out, written = _run_job(
        json.dumps({"order_id": 5}), {"ENVIRONMENT": "prod"}, tmp_path
    )
    assert out.status == "processed"
    assert written == {"order_id": 5, "status": "processed"}


def test_test_mode_skips(tmp_path):
    out, written = _run_job(
        json.dumps({"order_id": 5}), {"ENVIRONMENT": "test"}, tmp_path
    )
    assert out.status == "skipped"
    assert written["status"] == "skipped"


def test_should_run_false_skips(tmp_path):
    out, _ = _run_job(json.dumps({"order_id": 0}), {"ENVIRONMENT": "prod"}, tmp_path)
    assert out.status == "skipped"


def test_custom_task_token_env_var_is_honored(monkeypatch, tmp_path):
    # With a task token present, send_response takes the boto3 path — assert it tries to,
    # using a custom env var name (we stub boto3 so no network happens).
    sent = {}

    class _FakeClient:
        def send_task_success(self, taskToken, output):
            sent["token"] = taskToken
            sent["output"] = output

    import boto3

    monkeypatch.setattr(boto3, "client", lambda *a, **k: _FakeClient())
    monkeypatch.setenv("MY_TOKEN", "tok-123")
    monkeypatch.setenv("ENVIRONMENT", "prod")

    job = _Job(task_token_env_var="MY_TOKEN")
    job.execute(json.dumps({"order_id": 5}))
    assert sent == {
        "token": "tok-123",
        "output": Out(order_id=5, status="processed").model_dump_json(),
    }
