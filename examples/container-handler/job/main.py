"""A job written with BatchJobInterface (see ../../docs/container-handler.md)."""

import sys

from pydantic import BaseModel
from aws_stepfunctions_toolkit import BatchJobInterface


class In(BaseModel):
    order_id: int


class Out(BaseModel):
    order_id: int
    status: str


class MyJob(BatchJobInterface[In, Out]):
    input_model = In
    output_model = Out

    def should_run(self, i: In) -> bool:
        return True

    def run(self, i: In) -> Out:
        return Out(order_id=i.order_id, status="processed")

    def create_skip_output(self, i: In) -> Out:
        return Out(order_id=i.order_id, status="skipped")


if __name__ == "__main__":
    MyJob().execute(sys.argv[1])
