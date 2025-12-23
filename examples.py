from pathlib import Path

import boto3
from mypy_boto3_stepfunctions import SFNClient

from aws_stepfunctions_toolkit import DefinitionIterator
from aws_stepfunctions_toolkit.testing import StepFunctionDefinitionProcessor

if __name__ == "__main__":
    iterator = DefinitionIterator.from_file("data/definition.asl.json")
    for state in iterator:
        print(f"{state.name}: {state.type} ({type(state).__name__})")


    sfn: SFNClient = boto3.client('stepfunctions', region_name="us-east-1")
    state_machine_arn = "arn:aws:states:us-east-1:000000000000:stateMachine:UnigenStateMachine"
    output_path = "data/definition.asl.json"
    processor = StepFunctionDefinitionProcessor.from_arn(state_machine_arn, sfn)
    _ = processor.process_definition()
    processor.save_definition(Path(output_path))