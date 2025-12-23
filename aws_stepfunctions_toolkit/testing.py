"""Testing utilities module for AWS Step Functions mock data and definition generation."""

import json
import logging
import jmespath
from pathlib import Path
from typing import Any, Final
import boto3
from mypy_boto3_stepfunctions import SFNClient
from mypy_boto3_stepfunctions.type_defs import (
    HistoryEventTypeDef,
    DescribeExecutionOutputTypeDef,
    MockInputTypeDef,
    TestStateOutputTypeDef
)
from typing_extensions import TypedDict

from .history import ExecutionHistory
from .definition import DefinitionIterator


class AllOutput(TypedDict, total=False):
    mock: MockInputTypeDef
    type: str
    task: bool


RESOURCE_OUTPUT_PATTERNS: Final[dict[str, tuple[str, str]]] = {
    "arn:aws:states:::states:startExecution.sync:2": ("$states.result.Output", "$parse($states.result.Output)"),
    "arn:aws:states:::lambda:invoke": ("$states.result.Payload", "$parse($states.result.Payload)")
}


def _create_map_state_output(history: ExecutionHistory, state_name: str) -> AllOutput:
    """Create mock output for MapState by collecting iteration outputs."""
    outputs = []
    for event in history:
        i = event["id"] - 1
        if (
                event['type'] == 'MapIterationSucceeded' and
                event['mapIterationSucceededEventDetails']['name'] == state_name and
                i > 0
        ):
            prev_event = history[i - 1]
            if 'stateExitedEventDetails' in prev_event:
                output = prev_event['stateExitedEventDetails'].get('output')
                if output:
                    outputs.append(json.loads(output))

    return {"mock": {"result": json.dumps(outputs)}}


def _create_task_failed_output(failed_event: HistoryEventTypeDef) -> AllOutput:
    """Create mock output for failed task."""
    details = failed_event['taskFailedEventDetails']
    return {
        "mock": {
            "errorOutput": {
                "error": details["error"],
                "cause": details["cause"]
            }
        },
        "type": "task"
    }


def _create_step_function_output(output: dict[str, Any]) -> AllOutput:
    """Create mock output for Step Function execution."""
    output["Input"] = json.dumps(output["Input"])
    output["Output"] = json.dumps(output["Output"])
    output["StopDate"] = str(output["StopDate"])
    output["StartDate"] = str(output["StartDate"])
    return {
        "mock": {"result": json.dumps(output)},
        "task": False
    }


def _create_lambda_output(output: dict[str, Any]) -> AllOutput:
    """Create mock output for Lambda function."""
    result = {
        "Payload": json.dumps(output["Payload"]),
        "ExecutedVersion": output["ExecutedVersion"]
    }
    return {"mock": {"result": json.dumps(result)}}


def _create_generic_task_output(output: dict[str, Any]) -> AllOutput:
    """Create mock output for generic task."""
    return {
        "mock": {"result": json.dumps(output)},
        "task": True
    }


def _process_map_state_event(execution_history: ExecutionHistory, history_event: HistoryEventTypeDef) -> tuple[str, AllOutput]:
    """Process MapStateExited event."""
    state_name = history_event["stateExitedEventDetails"]["name"]
    return state_name, _create_map_state_output(execution_history, state_name)


def _process_task_state_event(history: ExecutionHistory, history_event: HistoryEventTypeDef) -> tuple[None, None] | tuple[str, AllOutput]:
    """Process TaskStateEntered event by iterating forward to find result."""
    state_name = history_event['stateEnteredEventDetails']['name']

    # Iterate forward to find TaskSucceeded or TaskFailed
    for result_event in history.iter(start=history_event):
        if result_event['type'] == "TaskFailed":
            return state_name, _create_task_failed_output(result_event)
        elif result_event['type'] == "TaskSucceeded":
            details = result_event["taskSucceededEventDetails"]
            output = json.loads(details['output'])

            if details["resource"] == "startExecution.sync:2":
                return state_name, _create_step_function_output(output)
            elif details["resourceType"] == "lambda":
                return state_name, _create_lambda_output(output)
            else:
                return state_name, _create_generic_task_output(output)

    return None, None


def _extract_state_outputs(execution_history: ExecutionHistory) -> dict[str, AllOutput]:
    """Extract state outputs from execution history."""
    state_outputs = {}

    for event in execution_history:
        if event['type'] == 'MapStateExited':
            state_name, output = _process_map_state_event(execution_history, event)
            state_outputs[state_name] = output

        elif event['type'] == 'TaskStateEntered':
            state_name, output = _process_task_state_event(execution_history, event)
            if state_name and output:
                state_outputs[state_name] = output

    return state_outputs


def _write_json_file(data: Any, filepath: str | Path) -> None:
    """Write data to JSON file with proper formatting."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)


class StepFunctionDefinitionProcessor(DefinitionIterator):
    """Processes Step Function definitions for testing by updating output parsing."""

    def _update_output_parsing(self, obj) -> None:
        """Recursively update output field parsing for specific resource types."""
        if isinstance(obj, dict):
            self._update_dict_output(obj)
            for value in obj.values():
                self._update_output_parsing(value)
        elif isinstance(obj, list):
            for item in obj:
                self._update_output_parsing(item)

    @staticmethod
    def _update_dict_output(obj: dict) -> None:
        """Update output parsing for a dictionary object."""
        resource = obj.get("Resource")
        if resource in RESOURCE_OUTPUT_PATTERNS and obj.get("Output"):
            old_pattern, new_pattern = RESOURCE_OUTPUT_PATTERNS[resource]
            obj["Output"] = obj["Output"].replace(old_pattern, new_pattern)

    def process_definition(self) -> dict:
        """Process definition by updating output parsing."""
        self._update_output_parsing(self.definition)
        return self.definition


def generate_mock_data(execution_arn: str, output_dir: str | Path = None, 
                      region: str = None, sfn_client: SFNClient = None) -> dict[str, Any]:
    """Generate mock data files from Step Functions execution."""
    if sfn_client is None:
        sfn_client = boto3.client('stepfunctions', region_name=region)
    
    if output_dir is None:
        execution_name = execution_arn.split(':')[-1]
        output_dir = Path(f"data/{execution_name}")
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get execution data using ExecutionHistory
    execution_history = ExecutionHistory.from_execution_arn(sfn_client, execution_arn)
    execution_response: DescribeExecutionOutputTypeDef = sfn_client.describe_execution(executionArn=execution_arn)
    execution_input = json.loads(execution_response['input'])
    state_outputs = _extract_state_outputs(execution_history)

    # Write output files
    _write_json_file(execution_history.events, output_dir / "history.json")
    _write_json_file(execution_input, output_dir / "input.json")
    _write_json_file(state_outputs, output_dir / "state_outputs.json")

    return {
        'history': execution_history.events,
        'execution_input': execution_input,
        'state_outputs': state_outputs,
        'output_dir': output_dir
    }


def generate_revised_definition(state_machine_arn: str, output_path: str | Path = None,
                               region: str = None, sfn_client: SFNClient = None) -> dict:
    """Generate revised definition from Step Functions state machine."""
    if sfn_client is None:
        sfn_client = boto3.client('stepfunctions', region_name=region)
    
    if output_path is None:
        output_path = Path("data/definition.asl.json")
    else:
        output_path = Path(output_path)
    
    processor = StepFunctionDefinitionProcessor.from_arn(state_machine_arn, sfn_client)
    definition = processor.process_definition()
    processor.save_definition(output_path)
    
    return definition


class StepFunctionTester:
    """Test Step Functions state machines using AWS test_state API."""
    
    def __init__(self, region="us-east-1"):
        self.client = boto3.client('stepfunctions', region_name=region)
        self.logger = logging.getLogger(__name__)
    
    def _create_base_context(self, state_input: dict) -> dict:
        return {
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
    
    def _get_context_for_state(self, state_name: str, definition: dict, base_context: dict) -> str:
        state_def = definition["States"][state_name]
        has_task_token = jmespath.search("Arguments.ContainerOverrides.Environment[?Name=='TaskToken']", state_def)
        
        if has_task_token:
            return json.dumps(base_context | {"Task": {"Token": "String"}})
        return json.dumps(base_context)
    
    def _test_state(self, definition: dict, state_input: str, state_name: str,
                   variables: dict, mocked_results: dict, base_context: dict) -> TestStateOutputTypeDef:
        params = {
            "definition": json.dumps(definition),
            "input": state_input,
            "stateName": state_name,
            "variables": json.dumps(variables)
        }
        
        if state_name in mocked_results:
            params["mock"] = mocked_results[state_name]["mock"]
            params["context"] = self._get_context_for_state(state_name, definition, base_context)
        
        return self.client.test_state(**params)
    
    def execute_state_machine(self, state_input: str, definition: dict,
                            mocked_results: dict, variables: dict):
        """Execute state machine with mocked results for testing."""
        base_context = self._create_base_context(json.loads(state_input))
        current_state = definition["StartAt"]
        self.logger.info(f"Starting execution at state: {current_state}")
        
        response = self._test_state(definition, state_input, current_state, variables, mocked_results, base_context)
        
        while response.get("nextState"):
            current_state = response["nextState"]
            self.logger.info(f"Transitioning to state: {current_state}")
            
            if response.get("error") and response["status"] != "CAUGHT_ERROR":
                raise Exception(f"State {current_state} failed: {response.get('error')} - {response.get('cause')}")
            
            response = self._test_state(definition, response["output"], current_state, variables, mocked_results, base_context)
        
        self.logger.info("Execution completed successfully")
