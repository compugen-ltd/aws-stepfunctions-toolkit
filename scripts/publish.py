#!/usr/bin/env python3
"""Cross-platform publish script for AWS CodeArtifact."""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], capture_output: bool = False) -> str:
    """Run a command and return output if requested."""
    try:
        result = subprocess.run(
            cmd, 
            capture_output=capture_output, 
            text=True, 
            check=True
        )
        return result.stdout.strip() if capture_output else ""
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(cmd)}")
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main publish function."""
    print("Getting CodeArtifact authorization token...")
    
    # Get the token
    token = run_command([
        "aws", "codeartifact", "get-authorization-token",
        "--domain", "cgen",
        "--domain-owner", "000000000000", 
        "--region", "us-east-1",
        "--query", "authorizationToken",
        "--output", "text"
    ], capture_output=True)
    
    # Set environment variables
    env = os.environ.copy()
    env["UV_PUBLISH_USERNAME"] = "aws"
    env["UV_PUBLISH_PASSWORD"] = token
    
    print("Building package...")
    run_command(["uv", "build"])
    
    print("Publishing to CodeArtifact...")
    subprocess.run(
        ["uv", "publish", "--index", "aws"],
        env=env,
        check=True
    )
    
    print("✅ Package published successfully!")


if __name__ == "__main__":
    main()