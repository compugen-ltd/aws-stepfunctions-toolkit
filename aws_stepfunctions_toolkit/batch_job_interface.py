"""Generic base class for the container-side handler of a Step Functions task.

A batch/container job that participates in a Step Functions workflow has a small,
repeated contract:

  1. parse + validate its input,
  2. optionally skip work (test mode, or "already done"),
  3. run, producing a typed output,
  4. return the result to the workflow — either via a task token
     (``.waitForTaskToken``) or by writing it to a local file (``OUTPUT_PATH``)
     so a local test harness can pick it up.

``BatchJobInterface`` encapsulates that contract. Subclasses supply their own
``input_model`` / ``output_model`` (any pydantic models) and implement
``should_run`` / ``run`` / ``create_skip_output``. Nothing here assumes a
particular input or output shape.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar, final

from pydantic import BaseModel


InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


# --- Optional convenience models (a common shape; not required by the base) ---
class LastStepResults(BaseModel):
    filepath: str


class BasicJobInput(BaseModel):
    last_step_results: LastStepResults
    force: bool = False


class BasicJobOutput(BaseModel):
    filepath: str
    did_run: bool


class BatchJobInterface(ABC, Generic[InputT, OutputT]):
    # Subclasses must set these class attributes to their own pydantic models.
    input_model: type[InputT]
    output_model: type[OutputT]

    def __init__(
        self,
        logger: logging.Logger | None = None,
        task_token_env_var: str = "TaskToken",
        output_path_env_var: str = "OUTPUT_PATH",
        test_mode_env_var: str = "ENVIRONMENT",
        test_mode_values: tuple[str, ...] = ("dev", "test"),
        region: str | None = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.task_token_env_var = task_token_env_var
        self.output_path_env_var = output_path_env_var
        self.test_mode_env_var = test_mode_env_var
        self.test_mode_values = test_mode_values
        self.region = region
        self.output: OutputT | None = None
        self.input_data: InputT | None = None
        self.skip: bool = False

    @abstractmethod
    def should_run(self, input_data: InputT) -> bool:
        """Return True if the job should actually do its work for this input."""

    @abstractmethod
    def run(self, input_data: InputT) -> OutputT:
        """Do the work and return the typed output."""

    @abstractmethod
    def create_skip_output(self, input_data: InputT) -> OutputT:
        """Build the output to return when the job is skipped (test mode / should_run False)."""

    def parse_input(self, raw_input: str) -> InputT:
        self.logger.info("Parsing and validating input")
        return self.input_model.model_validate_json(raw_input)

    def check_test_mode(self) -> bool:
        env = os.environ.get(self.test_mode_env_var, "").lower()
        is_test_mode = env in self.test_mode_values
        if is_test_mode:
            self.logger.info(f"Test mode active ({self.test_mode_env_var}={env})")
        return is_test_mode

    def send_response(self, response: OutputT) -> None:
        data = response.model_dump_json()
        token = os.environ.get(self.task_token_env_var)
        if token:
            import boto3
            from aws_stepfunctions_toolkit.workflow_runner._common import resolve_region

            client = boto3.client(
                "stepfunctions", region_name=resolve_region(self.region)
            )
            _ = client.send_task_success(taskToken=token, output=data)
        elif output_path := os.environ.get(self.output_path_env_var):
            Path(output_path).write_text(data)

    @final
    def execute(self, raw_input: str) -> OutputT:
        self.logger.info("Starting batch job execution")

        self.input_data = input_data = self.parse_input(raw_input)

        if self.check_test_mode():
            self.logger.info("Test mode active, skipping execution")
            output = self.create_skip_output(input_data)
            self.send_response(output)
            return output

        self.logger.info("Checking if job should run")
        if not self.should_run(input_data):
            self.skip = True
            self.logger.info("Job should not run, skipping execution")
            output = self.create_skip_output(input_data)
            self.send_response(output)
            return output

        self.logger.info("Executing job")
        self.output = output = self.run(input_data)

        self.logger.info("Job execution completed successfully")
        self.send_response(output)

        return output
