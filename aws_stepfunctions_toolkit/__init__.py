"""AWS Step Functions Toolkit.

Run Step Functions state machines end-to-end on your machine: the toolkit walks the
state machine, uses the AWS ``test_state`` API for the engine-side logic
(Path/Parameters/ResultSelector/next-state), and lets you plug in strategies for the
states the test API can't run remotely (``.sync`` Batch jobs, ``.waitForTaskToken``) —
typically by building and running their container locally via Docker.

Everything you need is importable from this top-level package.
"""
from importlib.metadata import version, PackageNotFoundError

# --- Engine + strategies + image sources + models ---
from .workflow_runner import (
    WorkflowRunner,
    StateExecutionStrategy,
    DockerBatchStrategy,
    BatchImageStrategy,
    LocalBatchImageStrategy,
    CallableStrategy,
    StaticMockResponseStrategy,
    BatchJobResponseStrategy,
    GetLatestConfigurationStrategy,
    AbstractMockMapResponseStrategy,
    StandardFlowStrategy,
    build_strategies,
    get_container_overrides,
    ImageSource,
    PrebuiltImage,
    DockerfileImage,
    BakeImage,
    login_to_ecr,
    get_codeartifact_token,
    ExecutionContext,
    StartExecutionResult,
    AslDefinition,
    AslDefinitionDict,
    DockerBatchConfig,
)

# --- Execution-history processing + mock-data generation (from real executions) ---
from .history import ExecutionHistory, EventFilter
from .testing import generate_mock_data

# --- Container-side handler base ---
from .batch_job_interface import (
    BatchJobInterface,
    BasicJobInput,
    BasicJobOutput,
    LastStepResults,
)

try:
    # Use the 'name' defined in the [project] section of pyproject.toml
    __version__ = version("aws-stepfunctions-toolkit")
except PackageNotFoundError:
    # package is not installed (e.g. during local development without pip install -e .)
    __version__ = "unknown"

__all__ = [
    # engine
    "WorkflowRunner",
    # strategies
    "StateExecutionStrategy",
    "DockerBatchStrategy",
    "BatchImageStrategy",
    "LocalBatchImageStrategy",
    "CallableStrategy",
    "StaticMockResponseStrategy",
    "BatchJobResponseStrategy",
    "GetLatestConfigurationStrategy",
    "AbstractMockMapResponseStrategy",
    "StandardFlowStrategy",
    "build_strategies",
    "get_container_overrides",
    # image sources
    "ImageSource",
    "PrebuiltImage",
    "DockerfileImage",
    "BakeImage",
    "login_to_ecr",
    "get_codeartifact_token",
    # models
    "ExecutionContext",
    "StartExecutionResult",
    "AslDefinition",
    "AslDefinitionDict",
    "DockerBatchConfig",
    # history + mock generation
    "ExecutionHistory",
    "EventFilter",
    "generate_mock_data",
    # container-side handler
    "BatchJobInterface",
    "BasicJobInput",
    "BasicJobOutput",
    "LastStepResults",
    "__version__",
]
