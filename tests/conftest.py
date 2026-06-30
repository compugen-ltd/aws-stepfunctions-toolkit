"""Shared pytest config.

- A region must be resolvable for boto3 client construction in the unit tests (no network
  or credentials are used there — clients are only constructed, never called).
- The example integration tests read `ROLE_ARN` (and friends) from the gitignored `data.env`
  at the repo root, so they run locally without exporting anything. `data.env` doesn't exist
  in CI, so those tests stay auto-skipped there. An already-exported env var always wins
  (override=False).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_REGION", "us-east-1")

load_dotenv(Path(__file__).resolve().parents[1] / "data.env", override=False)
