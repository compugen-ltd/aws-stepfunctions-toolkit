"""The 'batch job': reads its input arg, writes result JSON to OUTPUT_PATH."""

import json
import os
import sys
from pathlib import Path

data = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
result = {"processed": True, "input_seen": data}
Path(os.environ["OUTPUT_PATH"]).write_text(json.dumps(result))
