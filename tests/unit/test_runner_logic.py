"""Offline unit tests for WorkflowRunner's pure logic (no test_state calls).

Constructing a WorkflowRunner builds a boto3 client but never calls it here.
"""

import json

import pytest

from aws_stepfunctions_toolkit import WorkflowRunner
from aws_stepfunctions_toolkit.workflow_runner._common import resolve_region


ROLE = "arn:aws:iam::000000000000:role/dummy"
MAIN = {"StartAt": "A", "States": {"A": {"Type": "Pass", "End": True}}}


def _runner(asl=None, mock_mapping=None):
    return WorkflowRunner(
        role_arn=ROLE,
        asl_registry=asl or {"main": MAIN},
        mock_mapping=mock_mapping or {},
        region="us-east-1",
    )


def test_resolve_region_precedence(monkeypatch):
    assert resolve_region("eu-west-1") == "eu-west-1"
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
    assert resolve_region() == "ap-south-1"


def test_invalid_asl_is_rejected_at_construction():
    with pytest.raises(RuntimeError):
        _runner(asl={"main": {"States": {}}})  # missing StartAt


def test_has_token_detects_taskoken_env():
    r = _runner()
    with_token = {
        "Arguments": {
            "ContainerOverrides": {"Environment": [{"Name": "TaskToken", "Value": "x"}]}
        }
    }
    assert r.has_token(with_token) is True
    assert r.has_token({"Arguments": {}}) is False


def test_context_sets_state_name_and_input():
    r = _runner()
    ctx = json.loads(r._get_context_for_state({"Type": "Task"}, {"mem": {"S": 1}}, "S"))
    assert ctx["State"]["Name"] == "S"
    assert ctx["Execution"]["Input"]["mem"] == {"S": 1}


def test_context_includes_task_token_only_when_present():
    r = _runner()
    no_tok = json.loads(r._get_context_for_state({"Type": "Pass"}, {}, "S"))
    assert "Task" not in no_tok
    tok = json.loads(
        r._get_context_for_state(
            {
                "Arguments": {
                    "ContainerOverrides": {
                        "Environment": [{"Name": "TaskToken", "Value": "x"}]
                    }
                }
            },
            {},
            "S",
        )
    )
    assert tok["Task"]["Token"]


def test_alter_mock_step_rewrites_lambda_payload_only_when_mocked():
    state = {
        "Resource": "arn:aws:states:::lambda:invoke",
        "Output": "{% $states.result.Payload %}",
    }
    # Not in mock_mapping -> unchanged
    r = _runner(mock_mapping={})
    assert r.alter_mock_step("L", state)["Output"] == "{% $states.result.Payload %}"
    # In mock_mapping -> $parse rewrite
    r2 = _runner(mock_mapping={"L": object()})
    assert (
        r2.alter_mock_step("L", state)["Output"]
        == "{% $parse($states.result.Payload) %}"
    )


def test_format_definitions_rewrites_startexecution_output():
    asl = {
        "main": {
            "StartAt": "C",
            "States": {
                "C": {
                    "Resource": "arn:aws:states:::states:startExecution.sync:2",
                    "Output": "{% $states.result.Output %}",
                }
            },
        }
    }
    out = WorkflowRunner._format_definitions(asl)
    assert out["main"]["States"]["C"]["Output"] == "{% $parse($states.result.Output) %}"


def test_collect_all_state_names_recurses_map_and_parallel():
    asl = {
        "main": {
            "StartAt": "M",
            "States": {
                "M": {
                    "Type": "Map",
                    "ItemProcessor": {"States": {"Inner": {"Type": "Pass"}}},
                },
                "P": {
                    "Type": "Parallel",
                    "Branches": [{"States": {"B": {"Type": "Pass"}}}],
                },
            },
        }
    }
    names = _runner(asl=asl)._collect_all_state_names()
    assert {"M", "Inner", "P", "B"} <= names


def test_validate_start_requires_main():
    with pytest.raises(RuntimeError):
        WorkflowRunner(
            role_arn=ROLE,
            asl_registry={"notmain": MAIN},
            mock_mapping={},
            region="us-east-1",
        ).start({})
