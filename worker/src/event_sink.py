from typing import Protocol, runtime_checkable

from normalized_event import NormalizedEvent


@runtime_checkable
class EventSink(Protocol):
    def persist(self, event: NormalizedEvent) -> None:
        """Persist a normalized event in the configured destination."""
