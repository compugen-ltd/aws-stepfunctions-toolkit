"""
Unified interface framework for AWS Batch jobs.

This module provides a base class that encapsulates common patterns for batch jobs,
including input/output validation, test mode handling, execution orchestration,
and Step Functions integration.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar, Literal, final

from pydantic import BaseModel, Field


class LastStepResults(BaseModel):
    filepath: str = Field()

class BasicJobInput(BaseModel):
    last_step_results: LastStepResults = Field(
        description="Results from the previous pipeline step"
    )
    force: bool = Field(
        default=False,
        description="Force re-run even if the step has already been completed"
    )


class BasicJobOutput(BaseModel):
    filepath: str = Field()
    did_run: bool = Field(
        description="Whether the job actually executed (False if skipped)"
    )


InputT = TypeVar("InputT", bound=BasicJobInput)
OutputT = TypeVar("OutputT", bound=BasicJobOutput)


class BatchJobInterface(ABC, Generic[InputT, OutputT]):
    # Subclasses must set these class attributes
    input_model: type[InputT]
    output_model: type[OutputT]

    def __init__(
            self,
            logger: logging.Logger | None = None,
            task_token_env_var: str = "TaskToken",
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.task_token_env_var = task_token_env_var
        self.output: OutputT | None = None
        self.input_data: InputT | None = None
        self.skip: bool = False

    @abstractmethod
    def should_run(self, input_data: InputT) -> bool:
        return input_data.force

    @abstractmethod
    def run(self, input_data: InputT) -> OutputT:
        pass

    def parse_input(self, raw_input: str) -> InputT:
        self.logger.info("Parsing and validating input")
        return self.input_model.model_validate_json(raw_input)

    def check_test_mode(self) -> bool:
        env = os.environ.get("ENVIRONMENT", "").lower()
        is_test_mode = env in ("dev", "test")
        if is_test_mode:
            self.logger.info(f"Test mode active (ENVIRONMENT={env})")
        return is_test_mode

    def create_skip_output(self, filepath: str, filename: str) -> OutputT:
        return self.output_model(did_run=False, filepath=filepath, filename=filename)

    @abstractmethod
    def create_send_response_data(self) -> OutputT:
        return self.output_model(
            filepath=self.input_data.last_step_results.filepath
        )

    def send_response(self, response: OutputT):
        data = response.model_dump_json()
        if token := os.environ.get("TaskToken"):
            import boto3
            client = boto3.client("stepfunctions", region_name="us-east-1")
            _ = client.send_task_success(
                taskToken=token,
                output=data,
            )
        elif output_path := os.environ.get("OUTPUT_PATH"):
            Path(output_path).write_text(data)

    @final
    def execute(self, raw_input: str) -> OutputT:
        self.logger.info("Starting batch job execution")

        # Parse and validate input
        self.input_data = input_data = self.parse_input(raw_input)
        filepath = input_data.last_step_results.filepath
        filename = input_data.last_step_results.filename

        # Check test mode
        if self.check_test_mode():
            self.logger.info("Test mode active, skipping execution")
            output = self.create_skip_output(filepath=filepath, filename=filename)
            self.send_response(output)
            return output

        # Check if should run
        self.logger.info("Checking if job should run")
        if not self.should_run(input_data):
            self.skip = True
            self.logger.info("Job should not run, skipping execution")
            output = self.create_skip_output(filepath=filepath, filename=filename)
            self.send_response(output)
            return output

        # Execute job
        self.logger.info("Executing job")
        self.output = output = self.run(input_data)

        # Validate output (Pydantic validation happens in run() return)
        self.logger.info("Job execution completed successfully")

        # Send success to Step Functions
        resp = self.create_send_response_data()
        self.send_response(resp)

        return output
