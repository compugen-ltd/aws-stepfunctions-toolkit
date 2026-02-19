from __future__ import annotations

import os
import logging
import json
from typing import Final, TypedDict, NotRequired, TYPE_CHECKING, Mapping

import jmespath
import boto3
from mypy_boto3_stepfunctions.type_defs import MockInputTypeDef
from mypy_boto3_stepfunctions.client import SFNClient

if TYPE_CHECKING:
    from .strategies import StateExecutionStrategy

from .strategies import StandardFlowStrategy

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


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
        "context": NotRequired[str],
    },
)


# --- 5. Main Orchestrator ---
class WorkflowRunner:
    RESOURCE_OUTPUT_PATTERNS: Final[dict[str, tuple[str, str]]] = {
        "arn:aws:states:::states:startExecution.sync:2": ("$states.result.Output", "$parse($states.result.Output)"),
        "arn:aws:states:::lambda:invoke": ("$states.result.Payload", "$parse($states.result.Payload)"),
    }

    def __init__(
            self,
            role_arn: str,
            asl_registry: Mapping[str, dict],
            mock_mapping: Mapping[str, StateExecutionStrategy],
            variables: dict = None
    ):
        self.client: SFNClient = boto3.client('stepfunctions', region_name="us-east-1")
        self.role_arn = role_arn
        self.asl_registry = asl_registry
        self.default_strategy = StandardFlowStrategy()
        self.variables = variables or dict()
        self.mock_mapping = mock_mapping

    def _get_context_for_state(self, state_def: dict, state_input) -> str:
        base_context = {
            "Execution": {
                "Id": "String",
                "Input": state_input.copy(),
                "Name": "String",
                "RoleArn": "String",
                "StartTime": "2025-12-14T18:00:00Z",
                "RedriveCount": 12,
                "RedriveTime": "2025-12-14T18:00:00Z"
            },
            "State": {
                "EnteredTime": "2025-12-14T18:00:00Z",
                "Name": "String",
                "RetryCount": 12
            },
            "StateMachine": {
                "Id": "String",
                "Name": "String"
            }
        }
        has_task_token = jmespath.search("Arguments.ContainerOverrides.Environment[?Name=='TaskToken']", state_def)

        if has_task_token:
            return json.dumps(base_context | {"Task": {"Token": "String"}})
        return json.dumps(base_context)

    def get_asl(self, identifier):
        return self.asl_registry.get(identifier)

    def run_sub_machine(self, asl_def: dict, initial_input: dict, mock_mapping: Mapping[str, StateExecutionStrategy],
                        start_:str = None, end_:str=None, parent_path: str = ""):
        if start_:
            current_state = start_
        else:
            current_state = asl_def["StartAt"]

        data = initial_input

        while current_state:
            logger.info(f"{current_state=}")

            state_def = asl_def["States"][current_state]

            # Select Strategy: Try hierarchical key first, then flat key
            hierarchical_key = f"{parent_path}/{current_state}" if parent_path else current_state
            if hierarchical_key in mock_mapping:
                raw_result = mock_mapping[hierarchical_key].execute(
                    current_state, state_def, data, self,
                    context=self._get_context_for_state(state_def, initial_input),
                    parent_path=parent_path
                )
            elif current_state in mock_mapping:
                raw_result = mock_mapping[current_state].execute(
                    current_state, state_def, data, self,
                    context=self._get_context_for_state(state_def, initial_input),
                    parent_path=parent_path
                )
            else:
                raw_result = self.default_strategy.execute(
                    current_state, state_def, data, self, mock_mapping=mock_mapping,
                    context=self._get_context_for_state(state_def, initial_input),
                    parent_path=parent_path
                )

            # Let AWS handle the logic (Path, Parameters, ResultSelector)
            response = self.client.test_state(
                stateName=current_state,
                definition=json.dumps(asl_def),
                roleArn=self.role_arn,
                variables=json.dumps(self.variables),
                input=json.dumps(data),
                **raw_result
            )

            if response.get('status') == 'FAILED':
                raise RuntimeError(f"State {current_state} failed: {response.get('error')}\n{response.get('cause')}")

            data = json.loads(response['output'])

            if end_ and current_state == end_:
                break

            current_state = response.get('nextState')

        return data

    @staticmethod
    def _format_definitions(asl_registry: Mapping[str,dict]) -> Mapping[str,dict]:
        for asl_name, asl_def in asl_registry.items():
            states = asl_def["States"]
            for stage_name, state_def in states.items():
                resource = state_def.get("Resource")
                if resource and resource in WorkflowRunner.RESOURCE_OUTPUT_PATTERNS and state_def.get("Output"):
                    old_pattern, new_pattern = WorkflowRunner.RESOURCE_OUTPUT_PATTERNS[resource]
                    states[stage_name]["Output"] = state_def["Output"].replace(old_pattern, new_pattern)
            asl_registry[asl_name]["States"] = states
        return asl_registry

    def start(self, initial_input: dict, mock_mapping: Mapping[str, StateExecutionStrategy], start: str = None,
              end: str = None, parent_path: str = ""):

        self.asl_registry = self._format_definitions(self.asl_registry)

        main_definition = self.asl_registry["main"]
        return self.run_sub_machine(main_definition, initial_input, mock_mapping, start, end, parent_path)
