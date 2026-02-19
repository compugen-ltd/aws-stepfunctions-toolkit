from pathlib import Path
import os

import boto3
from mypy_boto3_stepfunctions import SFNClient

from aws_stepfunctions_toolkit import DefinitionIterator
from aws_stepfunctions_toolkit.testing import StepFunctionDefinitionProcessor

THIS_DIR = Path(__file__).parent

if __name__ == "__main__":
    definition_file = THIS_DIR.joinpath("definition.asl.json")
    iterator = DefinitionIterator.from_file(definition_file)
    for state in iterator:
        print(f"{state.name}: {state.type} ({type(state).__name__})")

    sfn: SFNClient = boto3.client('stepfunctions', region_name="us-east-1")
    sfn_name = os.environ["SFN_NAME"]
    account_id = os.environ["ACCOUNT_ID"]
    state_machine_arn = f"arn:aws:states:us-east-1:{account_id}:stateMachine:{sfn_name}"
    output_path = "data/definition.asl.json"
    processor = StepFunctionDefinitionProcessor.from_arn(state_machine_arn, sfn)
    _ = processor.process_definition()
    processor.save_definition(Path(output_path))