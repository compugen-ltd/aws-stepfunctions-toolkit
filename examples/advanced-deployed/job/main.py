"""Local 'batch job' for the advanced example — run by the toolkit, not in AWS.

Reads its input arg, writes result JSON to OUTPUT_PATH (the container contract).
"""
import json
import os
import sys
from pathlib import Path

data = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}

result = {"processed": True, "ran": "locally", "input_seen": data}

Path(os.environ["OUTPUT_PATH"]).write_text(json.dumps(result))
print(f"[job] wrote result to {os.environ['OUTPUT_PATH']}")
