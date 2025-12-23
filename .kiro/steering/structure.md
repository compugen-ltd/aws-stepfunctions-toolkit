# Project Structure

## File Organization
```
sfn_testing/
├── .kiro/                      # Kiro configuration and steering files
├── data/                       # Test data and execution results
│   ├── definition.asl.json     # Step Functions state machine definition
│   └── {execution_name}/       # Per-execution test data
│       ├── input.json          # Test input data
│       ├── state_outputs.json  # Mock state outputs
│       └── history.json        # Execution history
├── main.py                     # Primary test execution script
├── helpers.py                  # Utility functions
├── generate_testing_*.py       # Test data generation scripts
└── pyproject.toml             # Project dependencies and metadata
```

## Naming Conventions
- **Files**: snake_case for Python files
- **Directories**: lowercase with underscores
- **Variables**: snake_case following PEP 8
- **Functions**: snake_case with descriptive names
- **Constants**: UPPER_CASE

## Import Patterns
- Standard library imports first
- Third-party imports second
- Local imports last
- Use pathlib for file operations
- Import boto3 client as needed

## Configuration Standards
- JSON files for test data and state definitions
- Use pathlib.Path for file system operations
- Store execution-specific data in named subdirectories
- Maintain consistent logging with INFO level default


### Paths
- Always use `pathlib.Path` (from `pathlib`) for all filesystem paths.
- Do **not** use string concatenation for paths.
- Do **not** use `os.path` unless there is a hard requirement (prefer `Path` methods).
- Prefer returning/accepting `Path` objects at module boundaries when interacting with files.

**Examples**
```py
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "config" / "app.yaml"

data = CONFIG_PATH.read_text(encoding="utf-8")
````

---

### Static parameters and constants

* Always define static params (constants, config keys, fixed defaults) using `UPPER_SNAKE_CASE`.
* Keep constants near the top of the module (or in a dedicated `constants.py` if shared).
* Avoid “magic numbers/strings” inline; extract them into constants.

**Examples**

```py
DEFAULT_TIMEOUT_SECONDS = 30
MAX_RETRIES = 5
STEP_FUNCTIONS_REGION = "us-east-1"
STATE_MACHINE_NAME_PREFIX = "my-app-"
```

### Misc
* When using classes use `@staticmethod` is method is static.
* Use pep8 conventions. 
* Use typing for function parameters and return values.


### Typing
* When using typing use python 3.13 features. Use dict and not Dict. etc.
* Add function return value types
* Add function params types
