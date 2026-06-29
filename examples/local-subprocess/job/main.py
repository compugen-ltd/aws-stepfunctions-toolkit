"""A trivial 'batch job' run by the local-subprocess example.

The toolkit (via LocalExecutionStrategy) runs this as: python main.py '<input-json>'
and sets OUTPUT_PATH to a temp file. The job must write its result JSON there — the
same contract a real container would honor (see docs/container-handler.md).
"""
import json
import os
import sys
from pathlib import Path

raw_input = sys.argv[1] if len(sys.argv) > 1 else "{}"
data = json.loads(raw_input)

# The Step Functions `.sync` result for this state. The state's Output expression
# reads `$states.result.Output`, so we put our payload under "Output".
result = {"Output": {"processed": True, "input_seen": data}}

Path(os.environ["OUTPUT_PATH"]).write_text(json.dumps(result))
print(f"[job] wrote result to {os.environ['OUTPUT_PATH']}")
