"""Integration tests: run each example end-to-end and assert it exits cleanly.

These call the real `test_state` API, so they are auto-skipped unless ROLE_ARN is set.
Docker examples additionally skip unless a Docker daemon is reachable; examples that need
extra state (a real execution ARN, a deployed stack) skip unless that env is present.

A completeness guard (test_all_example_scripts_are_covered) runs offline and fails if any
example entry script isn't listed below — so new examples can't silently go untested.

Run in parallel:  uv run pytest tests/examples -n auto
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

# --- which scripts are tested, and how ---
# Run with just ROLE_ARN (no Docker, no extra infra):
SIMPLE = [
    "quickstart/run.py",
    "data-flow/run.py",
    "sub-range/run.py",
    "map-parallel/run.py",
    "local-subprocess/run.py",
    "container-handler/run.py",
]
# Need a Docker daemon (parametrized over both image sources):
DOCKER = ["docker-batch/run.py", "docker-batch/run_with_overrides.py"]
# Need extra state in the environment:
ENV_GATED = ["mock-generation/run.py", "advanced-deployed/run.py"]

COVERED = set(SIMPLE) | set(DOCKER) | set(ENV_GATED)

requires_role = pytest.mark.skipif(
    not os.environ.get("ROLE_ARN"),
    reason="set ROLE_ARN to run example integration tests",
)


def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True).returncode == 0
    except OSError:
        return False


def _run(script: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(extra_env or {})
    path = EXAMPLES / script
    return subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(path.parent),
    )


def test_all_example_scripts_are_covered():
    """Offline guard: every examples/*/run*.py must be in COVERED (so it gets a test)."""
    found = {p.relative_to(EXAMPLES).as_posix() for p in EXAMPLES.glob("*/run*.py")}
    missing = found - COVERED
    assert not missing, f"example scripts with no test: {sorted(missing)}"
    stale = COVERED - found
    assert not stale, f"COVERED lists scripts that no longer exist: {sorted(stale)}"


@requires_role
@pytest.mark.integration
@pytest.mark.parametrize("script", SIMPLE, ids=[s.split("/")[0] for s in SIMPLE])
def test_simple_example_runs(script):
    p = _run(script)
    assert p.returncode == 0, (
        f"{script} failed:\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"
    )


@requires_role
@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.parametrize("script", DOCKER)
@pytest.mark.parametrize("image_source", ["dockerfile", "bake"])
def test_docker_batch_example_runs(script, image_source):
    if not _docker_available():
        pytest.skip("Docker not available")
    p = _run(script, {"IMAGE_SOURCE": image_source})
    assert p.returncode == 0, (
        f"{script} ({image_source}) failed:\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"
    )


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("EXECUTION_ARN"), reason="set EXECUTION_ARN to a real execution"
)
def test_mock_generation_example_runs():
    p = _run("mock-generation/run.py")
    assert p.returncode == 0, (
        f"mock-generation failed:\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"
    )


@pytest.mark.integration
@pytest.mark.skipif(
    not all(
        os.environ.get(k) for k in ("STATE_MACHINE_ARN", "FUNCTION_ARN", "SFN_ROLE_ARN")
    ),
    reason="deploy the advanced stack and export its outputs to run this",
)
def test_advanced_deployed_example_runs():
    p = _run("advanced-deployed/run.py")
    assert p.returncode == 0, (
        f"advanced-deployed failed:\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"
    )
