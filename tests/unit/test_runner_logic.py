"""Offline unit tests for WorkflowRunner's pure logic (no test_state calls).

Constructing a WorkflowRunner builds a boto3 client but never calls it here.
"""

import json

import pytest

from aws_stepfunctions_toolkit import WorkflowRunner
from aws_stepfunctions_toolkit.workflow_runner._common import resolve_region


ROLE = "arn:aws:iam::000000000000:role/dummy"
MAIN = {"StartAt": "A", "States": {"A": {"Type": "Pass", "End": True}}}


def _with_roles(registry, role=ROLE):
    """Stamp a ROLE_ARN on every registry entry (each SM carries its own role)."""
    return {
        name: {**definition, "ROLE_ARN": role} for name, definition in registry.items()
    }


def _runner(asl=None, mock_mapping=None):
    return WorkflowRunner(
        asl_registry=_with_roles(asl or {"main": MAIN}),
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
            asl_registry=_with_roles({"notmain": MAIN}),
            mock_mapping={},
            region="us-east-1",
        ).start({})


def test_missing_role_arn_is_rejected_at_construction():
    with pytest.raises(RuntimeError, match="ROLE_ARN"):
        WorkflowRunner(
            asl_registry={"main": MAIN},  # no ROLE_ARN
            mock_mapping={},
            region="us-east-1",
        )


def test_role_for_returns_entry_role():
    r = _runner()
    assert r.role_for(r.asl_registry["main"]) == ROLE
    with pytest.raises(RuntimeError, match="ROLE_ARN"):
        r.role_for({"StartAt": "A", "States": {}})


class _FakeSFN:
    """Records the roleArn each test_state call runs under, driving a 2-SM flow."""

    def __init__(self):
        self.calls = []  # {"resource", "roleArn", "trace"}

    def test_state(self, **kw):
        resource = json.loads(kw["definition"]).get("Resource", "")
        trace = kw.get("inspectionLevel")
        self.calls.append(
            {"resource": resource, "roleArn": kw["roleArn"], "trace": trace}
        )
        if trace == "TRACE":
            # startExecution.sync:2 TRACE inspection: echo the input as the child's Input.
            return {
                "status": "SUCCEEDED",
                "inspectionData": {
                    "afterArguments": json.dumps({"Input": json.loads(kw["input"])})
                },
            }
        # A normal state execution: echo input as output, no next state.
        return {"status": "SUCCEEDED", "output": kw["input"], "nextState": None}


def test_active_role_switches_across_nested_state_machine_boundary():
    parent_role = "arn:aws:iam::000000000000:role/parent"
    child_role = "arn:aws:iam::000000000000:role/child"
    main = {
        "StartAt": "child_flow",
        "States": {
            "child_flow": {
                "Type": "Task",
                "Resource": "arn:aws:states:::states:startExecution.sync:2",
                "End": True,
            }
        },
    }
    child = {"StartAt": "C", "States": {"C": {"Type": "Pass", "End": True}}}

    runner = WorkflowRunner(
        asl_registry={
            "main": {**main, "ROLE_ARN": parent_role},
            "child_flow": {**child, "ROLE_ARN": child_role},
        },
        mock_mapping={},
        region="us-east-1",
    )
    fake = _FakeSFN()
    runner.client = fake
    runner.start({"n": 1})

    # The child SM's own state (Pass "C", no Resource) ran under the child role...
    child_calls = [c for c in fake.calls if c["resource"] == ""]
    assert child_calls and all(c["roleArn"] == child_role for c in child_calls)
    # ...and the parent's startExecution state ran under the parent role.
    parent_calls = [c for c in fake.calls if "startExecution" in c["resource"]]
    assert parent_calls and all(c["roleArn"] == parent_role for c in parent_calls)
    # Active role is restored to the parent after the nested run.
    assert runner.active_role_arn == parent_role
