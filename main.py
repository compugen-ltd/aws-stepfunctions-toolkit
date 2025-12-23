import json
import argparse
import logging
from pathlib import Path

from aws_stepfunctions_toolkit import StepFunctionTester


def load_json_file(file_path: Path) -> dict:
    with file_path.open('r') as f:
        return json.load(f)


def main():
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description='Test Step Functions state machine')
    parser.add_argument('execution_name', help='Step Functions execution name')
    args = parser.parse_args()
    
    data_dir = Path('data')
    execution_dir = data_dir / args.execution_name
    
    state_input = load_json_file(execution_dir / 'input.json')
    mocked_results = load_json_file(execution_dir / 'state_outputs.json')
    definition = load_json_file(data_dir / 'definition.asl.json')
    
    variables = {"workfolder": "asd"}
    
    tester = StepFunctionTester()
    tester.execute_state_machine(json.dumps(state_input), definition, mocked_results, variables)


if __name__ == "__main__":
    main()
