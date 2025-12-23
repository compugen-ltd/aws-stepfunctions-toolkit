"""Definition management module for AWS Step Functions."""

import json
from pathlib import Path
import boto3
from abc import ABC
from typing import Iterator
from mypy_boto3_stepfunctions import SFNClient


class State(ABC):
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
    
    @property
    def type(self) -> str:
        return self.config.get("Type", "")
    
    @property
    def comment(self) -> str:
        return self.config.get("Comment", "")
    
    @property
    def next(self) -> str:
        return self.config.get("Next", "")
    
    @property
    def end(self) -> bool:
        return self.config.get("End", False)


class TaskState(State):
    @property
    def resource(self) -> str:
        return self.config.get("Resource", "")
    
    @property
    def arguments(self) -> dict:
        return self.config.get("Arguments", {})
    
    @property
    def parameters(self) -> dict:
        return self.config.get("Parameters", {})
    
    @property
    def catch(self) -> list:
        return self.config.get("Catch", [])
    
    @property
    def retry(self) -> list:
        return self.config.get("Retry", [])


class ChoiceState(State):
    @property
    def choices(self) -> list:
        return self.config.get("Choices", [])
    
    @property
    def default(self) -> str:
        return self.config.get("Default", "")


class MapState(State):
    @property
    def items(self) -> str:
        return self.config.get("Items", "")
    
    @property
    def max_concurrency(self) -> str:
        return self.config.get("MaxConcurrency", "")
    
    @property
    def item_processor(self) -> dict:
        return self.config.get("ItemProcessor", {})
    
    @property
    def item_selector(self) -> dict:
        return self.config.get("ItemSelector", {})


class PassState(State):
    @property
    def assign(self) -> dict:
        return self.config.get("Assign", {})


class WaitState(State):
    @property
    def seconds(self) -> int:
        return self.config.get("Seconds", 0)
    
    @property
    def timestamp(self) -> str:
        return self.config.get("Timestamp", "")


class SucceedState(State):
    pass


class FailState(State):
    @property
    def error(self) -> str:
        return self.config.get("Error", "")
    
    @property
    def cause(self) -> str:
        return self.config.get("Cause", "")


class ParallelState(State):
    @property
    def branches(self) -> list:
        return self.config.get("Branches", [])


def create_state(name: str, config: dict) -> State:
    """Factory function to create appropriate state type."""
    state_type = config.get("Type", "")
    
    state_classes = {
        "Task": TaskState,
        "Choice": ChoiceState,
        "Map": MapState,
        "Pass": PassState,
        "Wait": WaitState,
        "Succeed": SucceedState,
        "Fail": FailState,
        "Parallel": ParallelState
    }
    
    state_class = state_classes.get(state_type, State)
    return state_class(name, config)


class DefinitionIterator:
    """Iterator for Step Functions definition states."""
    
    def __init__(self, definition: dict):
        self.definition = definition
    
    @classmethod
    def from_file(cls, file_path: str) -> 'DefinitionIterator':
        """Create iterator from JSON file."""
        with open(file_path) as f:
            definition = json.load(f)
        return cls(definition)
    
    @classmethod
    def from_arn(cls, state_machine_arn: str, client: SFNClient = None) -> 'DefinitionIterator':
        """Create iterator from Step Functions ARN."""
        if client is None:
            client = boto3.client('stepfunctions')
        response = client.describe_state_machine(stateMachineArn=state_machine_arn)
        definition = json.loads(response['definition'])
        return cls(definition)
    
    def __iter__(self) -> Iterator[State]:
        for state_name, state_config in self.definition["States"].items():
            yield create_state(state_name, state_config)

    def save_definition(self, output_path: Path) -> None:
        """Save processed definition to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w') as f:
            json.dump(self.definition, f, indent=2)
