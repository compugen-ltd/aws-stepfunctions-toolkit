"""A tiny Lambda handler used by the docker-lambda example.

It receives the event Step Functions would pass as the lambda:invoke Payload and
returns a plain dict — which DockerLambdaStrategy captures as the step's real output.
"""

from __future__ import annotations


def handler(event: dict, _context: object) -> dict:
    number = event["number"]
    return {"doubled": number * 2, "echo": event}
