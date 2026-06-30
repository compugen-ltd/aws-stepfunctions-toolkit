"""Shared pytest config.

A region must be resolvable for boto3 client construction in the unit tests (no network
or credentials are used — clients are only constructed, never called).
"""

import os

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_REGION", "us-east-1")
