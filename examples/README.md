# Examples

Each subfolder is a **self-contained** example: its own ASL definition(s), a runnable script, a
README with hands-on steps, and any supporting files. Copy a folder, set `ROLE_ARN`, and run.

All examples call the real `test_state` API, so they need AWS credentials + a region and an IAM
role allowed to call it — see the [Setup guide](../docs/setup.md). Only the Docker example needs
Docker.

## Available examples

| Folder | Shows | Needs Docker? |
|--------|-------|---------------|
| [`quickstart/`](quickstart/) | Local end-to-end run; mocking steps with a fixed payload (`StaticMockResponseStrategy`) and your own function (`CallableStrategy`). | No |
| [`local-subprocess/`](local-subprocess/) | Running a step's code directly on your machine as a subprocess (`LocalExecutionStrategy`). | No |
| [`docker-batch/`](docker-batch/) | Running steps in real local containers (`DockerBatchStrategy`), both image sources (`DockerfileImage` + `BakeImage`), plus a nested state machine and a Lambda step. | Yes |

## Planned / not yet here

These features are documented (with snippets) rather than shipped as folders — several can only
run against real AWS state, so a copy-and-run folder would be misleading:

- **Map & Parallel**, **running a sub-range** → [docs/control-flow.md](../docs/control-flow.md)
- **Real AWS Batch submission** (`BatchJobResponseStrategy`) → [docs/strategies.md](../docs/strategies.md)
- **Container-side handler** (`BatchJobInterface`) → [docs/container-handler.md](../docs/container-handler.md)
- **Mock generation from a real execution** + history → [docs/cli-and-history.md](../docs/cli-and-history.md)
