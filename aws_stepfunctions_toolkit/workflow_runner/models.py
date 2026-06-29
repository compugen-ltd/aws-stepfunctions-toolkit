from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Json


# --- Execution Context (AWS spec) ---
# Cannot use `from __future__ import annotations` — breaks Pydantic field resolution for nested models.

class _Execution(BaseModel):
    Id: str = "String"
    Input: Json = "{}"
    Name: str = "String"
    RoleArn: str = "String"
    StartTime: str = "2025-12-14T18:00:00Z"
    RedriveCount: int = 12
    RedriveTime: str = "2025-12-14T18:00:00Z"


class _State(BaseModel):
    EnteredTime: str = "2025-12-14T18:00:00Z"
    Name: str = "String"
    RetryCount: int = 12


class _StateMachine(BaseModel):
    Id: str = "String"
    Name: str = "String"


class _Task(BaseModel):
    Token: str = "String"


class ExecutionContext(BaseModel):
    Execution: _Execution = _Execution()
    State: _State = _State()
    StateMachine: _StateMachine = _StateMachine()
    Task: _Task | None = None

    def with_input(self, state_input: dict) -> "ExecutionContext":
        self.Execution.Input = state_input.copy()
        return self

    def with_task_token(self) -> "ExecutionContext":
        self.Task = _Task()
        return self


# --- StartExecution.sync:2 mock result ---
# The ARNs below are inert placeholders: this object only exists so the test API
# accepts a well-formed mock wrapper for a nested-state-machine call. The account,
# region and state-machine name in these defaults do not affect any behavior.
class StartExecutionResult(BaseModel):
    OutputDetails: dict = {"Included": False}
    Input: str = ""
    ExecutionArn: str = "arn:aws:states:us-east-1:000000000000:execution:ExampleStateMachine:test"
    RedriveCount: int = 0
    InputDetails: dict = {"Included": False}
    RedriveStatus: str = "NOT_REDRIVABLE"
    RedriveStatusReason: str = "Execution is SUCCEEDED and cannot be redriven"
    StartDate: str = "1769015654832"
    StateMachineArn: str = "arn:aws:states:us-east-1:000000000000:stateMachine:ExampleStateMachine"
    Status: str = "SUCCEEDED"
    StopDate: str = "1769015943200"
    Output: str | None = None


# --- ASL Definition validation ---
class AslDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")
    StartAt: str
    States: dict


class AslDefinitionDict(TypedDict):
    StartAt: str
    States: dict[str, dict]


# --- Docker Batch Config ---
class DockerBatchConfig(BaseModel):
    s3_bucket: str
    bake_file: str
    volumes: list = []
    variables: dict = {}
    target_mapping: dict[str, str]
    user: str | None = None
