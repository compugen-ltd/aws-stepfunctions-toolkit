"""Testing utilities module for AWS Step Functions mock data and definition generation."""

import json
from pathlib import Path
from typing import Any, Final

import boto3
from typing_extensions import TypedDict
from mypy_boto3_stepfunctions import SFNClient
from mypy_boto3_stepfunctions.type_defs import (
    HistoryEventTypeDef,
    DescribeExecutionOutputTypeDef,
    MockInputTypeDef,
)

from .history import ExecutionHistory


class AllOutput(TypedDict, total=False):
    mock: MockInputTypeDef
    type: str
    task: bool


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

