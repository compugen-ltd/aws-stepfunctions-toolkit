from pathlib import Path
import sys
import os
import pydantic


class Input(pydantic.BaseModel):
    data: str

class Output(pydantic.BaseModel):
    data: str

def send_response(response):
    data = response.model_dump_json()
    if token := os.environ.get("TaskToken"):
        import boto3
        client = boto3.client("stepfunctions", region_name=os.environ.get("AWS_REGION"))
        _ = client.send_task_success(
            taskToken=token,
            output=data,
        )
    elif output_path := os.environ.get("OUTPUT_PATH"):
        Path(output_path).write_text(data)

raw_input = sys.argv[1]
input_ = Input.model_validate_json(raw_input)
send_response(input_)