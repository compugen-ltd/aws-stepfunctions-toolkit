# AWS Step Functions Toolkit

A Python package providing convenient tools for managing AWS Step Functions definitions and history events, with utilities for generating mock data and revised definitions for testing.

## Features

- **Definition Management**: Iterate and process Step Functions state definitions
- **History Processing**: Filter and analyze execution history events  
- **Mock Data Generation**: Extract mock data from executions for testing
- **Definition Processing**: Generate revised definitions optimized for testing
- **CLI Interface**: Command-line tools for common operations

## Installation

```bash
pip install aws-stepfunctions-toolkit
```

## Quick Start

### CLI Usage

Generate mock data from an execution:
```bash
sfn-toolkit generate-mock arn:aws:states:region:account:execution:MyStateMachine:execution-name
```

Generate revised definition from state machine:
```bash
sfn-toolkit generate-definition arn:aws:states:region:account:stateMachine:MyStateMachine
```

### Programmatic Usage

```python
from aws_stepfunctions_toolkit import DefinitionIterator, ExecutionHistory, generate_mock_data

# Iterate state definitions
iterator = DefinitionIterator.from_arn("arn:aws:states:...")
for state in iterator:
    print(f"{state.name}: {state.type}")

# Process execution history
history = ExecutionHistory.from_execution_arn(sfn_client, "arn:aws:states:...")
task_events = history.filter.by_type("TaskStateEntered")

# Generate mock data
result = generate_mock_data("arn:aws:states:...")
```

## Configuration

Set environment variables for defaults:
- `SFN_REGION`: Default AWS region
- `SFN_PROFILE`: Default AWS profile

## State Types

The toolkit supports all Step Functions state types with typed properties:
- `TaskState`: Lambda, service integrations
- `ChoiceState`: Conditional branching
- `MapState`: Parallel processing
- `ParallelState`: Concurrent execution
- `PassState`, `WaitState`, `SucceedState`, `FailState`

## CLI Commands

### generate-mock
Extract mock data from Step Functions execution for testing.

**Usage:**
```bash
sfn-toolkit generate-mock EXECUTION_ARN [OPTIONS]
```

**Options:**
- `--output-dir, -o`: Output directory (default: data/{execution-name})
- `--region, -r`: AWS region
- `--profile, -p`: AWS profile

**Output Files:**
- `history.json`: Complete execution history
- `input.json`: Execution input
- `state_outputs.json`: Mock outputs for each state

### generate-definition
Generate revised definition optimized for testing.

**Usage:**
```bash
sfn-toolkit generate-definition STATE_MACHINE_ARN [OPTIONS]
```

**Options:**
- `--output-path, -o`: Output file path (default: data/definition.asl.json)
- `--region, -r`: AWS region  
- `--profile, -p`: AWS profile

## API Reference

### DefinitionIterator
Iterator for Step Functions state definitions.

```python
# From file
iterator = DefinitionIterator.from_file("definition.json")

# From ARN
iterator = DefinitionIterator.from_arn("arn:aws:states:...")

# Iterate states
for state in iterator:
    print(state.name, state.type)
```

### ExecutionHistory
Process execution history events with filtering.

```python
history = ExecutionHistory.from_execution_arn(client, execution_arn)

# Filter events
lambda_events = history.filter.by_resource_type("lambda")
state_events = history.filter.by_state_name("MyState")
```

### Testing Functions

```python
# Generate mock data
result = generate_mock_data(
    execution_arn="arn:aws:states:...",
    output_dir="test_data"
)

# Generate revised definition  
definition = generate_revised_definition(
    state_machine_arn="arn:aws:states:...",
    output_path="revised_definition.json"
)
```