"""History management module for AWS Step Functions execution events."""

from mypy_boto3_stepfunctions import SFNClient
from mypy_boto3_stepfunctions.type_defs import HistoryEventTypeDef
from typing import Iterator


class EventFilter:
    """Filter methods for execution history events."""

    def __init__(self, events: list[HistoryEventTypeDef]):
        self.events = events

    def by_type(self, event_type: str) -> list[HistoryEventTypeDef]:
        """Return all events matching the given type."""
        return [e for e in self.events if e.get("type") == event_type]

    def by_state_name(self, state_name: str) -> list[HistoryEventTypeDef]:
        """Return all events from state entry until next state entry."""
        result = []
        capturing = False

        for event in self.events:
            if event.get("stateEnteredEventDetails", {}).get("name") == state_name:
                capturing = True
                result.append(event)
            elif capturing and event.get("stateEnteredEventDetails", {}).get("name"):
                break
            elif capturing:
                result.append(event)

        return result

    def by_resource_type(self, resource_type: str) -> list[HistoryEventTypeDef]:
        """Return all task events matching the resource type."""
        return [
            e
            for e in self.events
            if e.get("taskStartedEventDetails", {}).get("resourceType") == resource_type
        ]

    def by_resource(self, resource: str) -> list[HistoryEventTypeDef]:
        """Return all task events matching the resource."""
        return [
            e
            for e in self.events
            if e.get("taskStartedEventDetails", {}).get("resource") == resource
        ]


class ExecutionHistory:
    """Iterator for Step Functions execution history events."""

    def __init__(self, events: list[HistoryEventTypeDef]):
        self.events = events
        self.filter = EventFilter(events)

    @classmethod
    def from_execution_arn(
        cls, sfn_client: SFNClient, execution_arn: str
    ) -> "ExecutionHistory":
        """Retrieve complete execution history with pagination."""
        history = []
        next_token = None

        while True:
            params = {"executionArn": execution_arn}
            if next_token:
                params["nextToken"] = next_token

            response = sfn_client.get_execution_history(**params)
            history.extend(response["events"])
            next_token = response.get("nextToken")

            if not next_token:
                break

        return cls(history)

    def __iter__(self) -> Iterator[HistoryEventTypeDef]:
        """Iterate over history events."""
        for event in self.events:
            yield event

    def iter(
        self, start: int | HistoryEventTypeDef = None
    ) -> Iterator[HistoryEventTypeDef]:
        """Iterate over history events starting from given index."""
        if start is None:
            start_idx = 0
        elif isinstance(start, int):
            start_idx = start
        elif isinstance(start, dict) and "id" in start:
            start_idx = start["id"] - 1
        else:
            raise ValueError(f"Invalid start type: {type(start)}")

        for event in self.events[start_idx:]:
            yield event

    def __getitem__(self, index: int) -> HistoryEventTypeDef:
        """Get event by index."""
        return self.events[index]

    def __len__(self) -> int:
        """Get number of events."""
        return len(self.events)
