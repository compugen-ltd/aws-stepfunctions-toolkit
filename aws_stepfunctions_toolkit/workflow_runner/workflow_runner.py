from __future__ import annotations

import os
import logging
import json
from typing import Final, TYPE_CHECKING, Mapping, Callable

import jmespath
import boto3
from pydantic import ValidationError
from mypy_boto3_stepfunctions.client import SFNClient

if TYPE_CHECKING:
    from .strategies import StateExecutionStrategy

from ._common import resolve_region
from .strategies import StandardFlowStrategy
from .models import AslDefinition, AslDefinitionDict, ExecutionContext

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


# --- Main Orchestrator ---
class WorkflowRunner:
    RESOURCE_OUTPUT_PATTERNS: Final[dict[str, tuple[str, str]]] = {
        "arn:aws:states:::states:startExecution.sync:2": (
            "$states.result.Output",
            "$parse($states.result.Output)",
        ),
    }

    def __init__(
        self,
        role_arn: str,
        asl_registry: Mapping[str, AslDefinitionDict],
        mock_mapping: Mapping[str, StateExecutionStrategy],
        variables: dict | None = None,
        input_validation_function: Callable[[dict], None] | None = None,
        region: str | None = None,
    ):
        self.client: SFNClient = boto3.client(
            "stepfunctions", region_name=resolve_region(region)
        )
        self.role_arn = role_arn
        self.default_strategy = StandardFlowStrategy()
        self.variables = variables or dict()
        self.mock_mapping = mock_mapping
        self.input_validation_function = input_validation_function

        for name, definition in asl_registry.items():
            try:
                AslDefinition.model_validate(definition)
            except ValidationError as e:
                raise RuntimeError(f"Invalid ASL definition '{name}':\n{e}") from e
        self.asl_registry = asl_registry

    def has_token(self, state_def: dict) -> bool:
        return (
            jmespath.search(
                "Arguments.ContainerOverrides.Environment[?Name=='TaskToken']",
                state_def,
            )
            is not None
        )

    def _get_context_for_state(
        self, state_def: dict, state_input, state_name: str
    ) -> str:
        ctx = ExecutionContext().with_input(state_input)
        ctx.State.Name = (
            state_name  # so ASL expressions like $states.context.State.Name resolve
        )
        if self.has_token(state_def):
            ctx = ctx.with_task_token()
        return ctx.model_dump_json(exclude_none=True)

    def get_asl(self, identifier):
        result = self.asl_registry.get(identifier)
        if result is None:
            logger.warning(
                f"ASL '{identifier}' not found in registry. "
                f"Available: {list(self.asl_registry.keys())}"
            )
        return result

    def alter_mock_step(self, state_name: str, state_def: dict) -> dict:
        if state_name not in self.mock_mapping:
            return state_def
        resource = state_def.get("Resource", "")
        output = state_def.get("Output")
        if resource == "arn:aws:states:::lambda:invoke" and output:
            return {
                **state_def,
                "Output": output.replace(
                    "$states.result.Payload", "$parse($states.result.Payload)"
                ),
            }
        return state_def

    def run_sub_machine(
        self,
        asl_def: AslDefinitionDict,
        initial_input: dict,
        mock_mapping: Mapping[str, StateExecutionStrategy],
        start_: str | None = None,
        end_: str | None = None,
        parent_path: str = "",
    ) -> dict:
        current_state = start_ or asl_def["StartAt"]
        data = initial_input

        while current_state:
            if current_state not in asl_def["States"]:
                raise RuntimeError(
                    f"State '{current_state}' not found in definition. "
                    f"Available states: {list(asl_def['States'].keys())}"
                )

            logger.info(f"Running state: {current_state}")
            state_def = asl_def["States"][current_state]

            # Select Strategy: Try hierarchical key first, then flat key
            hierarchical_key = (
                f"{parent_path}/{current_state}" if parent_path else current_state
            )
            if hierarchical_key in mock_mapping:
                strategy = mock_mapping[hierarchical_key]
                raw_result = strategy.execute(
                    current_state,
                    state_def,
                    data,
                    self,
                    context=self._get_context_for_state(
                        state_def, initial_input, current_state
                    ),
                    parent_path=parent_path,
                )
            elif current_state in mock_mapping:
                strategy = mock_mapping[current_state]
                raw_result = strategy.execute(
                    current_state,
                    state_def,
                    data,
                    self,
                    context=self._get_context_for_state(
                        state_def, initial_input, current_state
                    ),
                    parent_path=parent_path,
                )
            else:
                strategy = self.default_strategy
                raw_result = strategy.execute(
                    current_state,
                    state_def,
                    data,
                    self,
                    mock_mapping=mock_mapping,
                    context=self._get_context_for_state(
                        state_def, initial_input, current_state
                    ),
                    parent_path=parent_path,
                )

            logger.debug(f"Strategy for '{current_state}': {type(strategy).__name__}")

            # Let AWS handle the logic (Path, Parameters, ResultSelector)
            response = self.client.test_state(
                definition=json.dumps(self.alter_mock_step(current_state, state_def)),
                roleArn=self.role_arn,
                variables=json.dumps(self.variables),
                input=json.dumps(data),
                **raw_result,
            )

            if response.get("status") == "FAILED":
                raise RuntimeError(
                    f"State '{current_state}' failed.\n"
                    f"  Error: {response.get('error')}\n"
                    f"  Cause: {response.get('cause')}\n"
                    f"  Input keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
                )

            raw_output = response.get("output")
            if raw_output is None:
                raise RuntimeError(
                    f"State '{current_state}' returned no output. "
                    f"Status: {response.get('status')}, "
                    f"Response keys: {list(response.keys())}"
                )
            try:
                data = json.loads(raw_output)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"State '{current_state}' returned invalid JSON output: {raw_output[:200]}"
                ) from e

            if end_ and current_state == end_:
                break

            next_state = response.get("nextState")
            logger.debug(f"{current_state} -> {next_state}")
            current_state = next_state

        return data

    def _collect_all_state_names(self) -> set[str]:
        names: set[str] = set()

        def _recurse(states: dict):
            for state_name, state_def in states.items():
                names.add(state_name)
                if "ItemProcessor" in state_def:
                    _recurse(state_def["ItemProcessor"].get("States", {}))
                for branch in state_def.get("Branches", []):
                    _recurse(branch.get("States", {}))

        for asl_def in self.asl_registry.values():
            _recurse(asl_def["States"])
        return names

    @staticmethod
    def _format_definitions(
        asl_registry: Mapping[str, AslDefinitionDict],
    ) -> Mapping[str, AslDefinitionDict]:
        for asl_name, asl_def in asl_registry.items():
            states = asl_def["States"]
            for stage_name, state_def in states.items():
                resource = state_def.get("Resource")
                if (
                    resource
                    and resource in WorkflowRunner.RESOURCE_OUTPUT_PATTERNS
                    and state_def.get("Output")
                ):
                    old_pattern, new_pattern = WorkflowRunner.RESOURCE_OUTPUT_PATTERNS[
                        resource
                    ]
                    states[stage_name]["Output"] = state_def["Output"].replace(
                        old_pattern, new_pattern
                    )
            asl_registry[asl_name]["States"] = states
        return asl_registry

    def _validate_start(
        self, initial_input: dict, mock_mapping: Mapping[str, StateExecutionStrategy]
    ):
        if self.input_validation_function:
            self.input_validation_function(initial_input)

        if "main" not in self.asl_registry:
            raise RuntimeError(
                f"'main' not found in ASL registry. Available: {list(self.asl_registry.keys())}. "
                f"Pass asl_registry={{'main': your_definition, ...}} when constructing WorkflowRunner."
            )

        all_state_names = self._collect_all_state_names()
        mock_keys = {k.split("/")[-1] for k in mock_mapping.keys()}
        unknown_keys = mock_keys - all_state_names
        if unknown_keys:
            logger.warning(
                f"mock_mapping contains keys not found in any ASL definition: {sorted(unknown_keys)}. "
                f"Available states: {sorted(all_state_names)}"
            )

    def start(
        self,
        initial_input: dict,
        start: str | None = None,
        end: str | None = None,
        parent_path: str = "",
    ):
        self.asl_registry = self._format_definitions(self.asl_registry)
        self._validate_start(initial_input, self.mock_mapping)

        main_definition = self.asl_registry["main"]
        return self.run_sub_machine(
            main_definition, initial_input, self.mock_mapping, start, end, parent_path
        )
