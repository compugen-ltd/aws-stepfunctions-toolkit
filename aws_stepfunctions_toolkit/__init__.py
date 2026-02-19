"""AWS Step Functions Toolkit - Tools for managing Step Functions definitions and history events."""
from importlib.metadata import version, PackageNotFoundError

from .history import ExecutionHistory, EventFilter
from .testing import generate_mock_data

try:
    # Use the 'name' defined in the [project] section of pyproject.toml
    __version__ = version("aws-stepfunctions-toolkit")
except PackageNotFoundError:
    # package is not installed (e.g. during local development without pip install -e .)
    __version__ = "unknown"

__all__ = [
    "ExecutionHistory", "EventFilter","generate_mock_data",
]
