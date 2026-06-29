# Examples

Each subfolder is a **self-contained** example: its own ASL definition(s), a runnable script, a
README with hands-on steps, and any supporting files. Copy a folder, set `ROLE_ARN`, and run.

All examples call the real `test_state` API, so they need AWS credentials + a region and an IAM
role allowed to call it — see the [Setup guide](../docs/setup.md). Only `docker-batch` needs
Docker; only `advanced-deployed` provisions AWS resources.

| Folder | Shows | Extra prereqs |
|--------|-------|---------------|
| [`quickstart/`](quickstart/) | Local end-to-end run; mocking steps with a fixed payload (`StaticMockResponseStrategy`) and your own function (`CallableStrategy`). | — |
| [`local-subprocess/`](local-subprocess/) | Running a step's code directly as a local subprocess (`LocalExecutionStrategy`). | — |
| [`container-handler/`](container-handler/) | A job written with `BatchJobInterface` (the container-side contract), run locally. | — |
| [`map-parallel/`](map-parallel/) | `Map` (fan-out) and `Parallel` (branches), handled automatically. | — |
| [`sub-range/`](sub-range/) | Running only part of a machine with `start` / `end`. | — |
| [`docker-batch/`](docker-batch/) | Steps in real local containers (`DockerBatchStrategy`); both image sources (`DockerfileImage` + `BakeImage`); a nested state machine; a Lambda step. | Docker |
| [`mock-generation/`](mock-generation/) | Generating mock data from a real execution + history inspection (`generate_mock_data`, `ExecutionHistory`). | a real execution ARN |
| [`advanced-deployed/`](advanced-deployed/) | Deploy a state machine + Lambda (CloudFormation), then run locally: invoke the **real** Lambda + run a **local** script step. | deploys AWS resources |

New here? Start with [`quickstart/`](quickstart/).
