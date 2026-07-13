"""Advanced: run a DEPLOYED state machine locally — real Lambda + a local script step.

Deploy infra/template.yaml (see README), export its outputs, then: python run.py
"""

import json
import os
import sys
from pathlib import Path

import boto3
from aws_stepfunctions_toolkit import (
    WorkflowRunner,
    CallableStrategy,
    LocalExecutionStrategy,
)

STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]
FUNCTION_ARN = os.environ["FUNCTION_ARN"]
ROLE_ARN = os.environ["SFN_ROLE_ARN"]

HERE = Path(__file__).parent
sfn = boto3.client("stepfunctions")
lam = boto3.client("lambda")

# Use the DEPLOYED state machine's definition.
definition = json.loads(
    sfn.describe_state_machine(stateMachineArn=STATE_MACHINE_ARN)["definition"]
)


def invoke_real_lambda(input_data: dict):
    resp = lam.invoke(
        FunctionName=FUNCTION_ARN, Payload=json.dumps(input_data).encode()
    )
    payload = json.loads(resp["Payload"].read())
    return {
        "Payload": json.dumps(payload)
    }  # Payload as a JSON string (toolkit convention)


mock_mapping = {
    "Enrich": CallableStrategy(invoke_real_lambda),  # triggers the REAL Lambda
    "ProcessLocally": LocalExecutionStrategy(
        entrypoint=[sys.executable, str(HERE / "job" / "main.py")]
    ),  # local script
}

runner = WorkflowRunner(
    asl_registry={"main": {**definition, "ROLE_ARN": ROLE_ARN}},
    mock_mapping=mock_mapping,
)
print(json.dumps(runner.start(initial_input={"order_id": 123}), indent=2))
