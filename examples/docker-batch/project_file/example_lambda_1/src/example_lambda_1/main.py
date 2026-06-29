from __future__ import annotations

from typing import TypedDict

from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel


class RespBody(TypedDict):
    key: str


class Resp(TypedDict):
    statusCode: int
    body: RespBody


class Request(BaseModel):
    key: str


@event_parser(model=Request)
def handler(event: Request, _: LambdaContext) -> Resp:
    print(event)
    return {"statusCode": 200, "body": {"key": "val"}}
