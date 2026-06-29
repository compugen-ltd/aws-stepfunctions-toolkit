"""Generate mock data from a REAL past execution, then inspect its history.

Set EXECUTION_ARN to one of your completed executions (needs AWS creds + a region;
no role_arn needed — it only reads the execution). Run:
    EXECUTION_ARN=arn:aws:states:...:execution:MyMachine:run-1  python run.py
"""
import os

import boto3
from aws_stepfunctions_toolkit import generate_mock_data, ExecutionHistory

EXECUTION_ARN = os.environ.get(
    "EXECUTION_ARN",
    "arn:aws:states:<region>:<account>:execution:MyStateMachine:exec-name",
)

result = generate_mock_data(EXECUTION_ARN, output_dir="mock_data")
print("wrote mock data to:", result["output_dir"])
print("states captured:", list(result["state_outputs"].keys()))

history = ExecutionHistory.from_execution_arn(boto3.client("stepfunctions"), EXECUTION_ARN)
print("total events:", len(history))
print("task-entered events:", len(history.filter.by_type("TaskStateEntered")))
