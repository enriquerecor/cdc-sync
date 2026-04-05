from dataclasses import dataclass

from event_sink import EventSink
from normalized_event import NormalizedEvent, Operation


@dataclass
class InMemoryEventSink:
    persisted_events: list[NormalizedEvent]

    def persist(self, event: NormalizedEvent) -> None:
        self.persisted_events.append(event)


class InvalidEventSink:
    def write(self, event: NormalizedEvent) -> None:
        self.event = event


def test_event_sink_protocol_accepts_persist_method() -> None:
    sink = InMemoryEventSink(persisted_events=[])

    event = NormalizedEvent(
        table="customers",
        primary_key={"id": 1},
        data={"id": 1, "email": "sink@example.com"},
        version=101,
        deleted=False,
        operation=Operation.INSERT,
    )

    sink.persist(event)

    assert isinstance(sink, EventSink)
    assert sink.persisted_events == [event]


def test_event_sink_protocol_rejects_missing_persist_method() -> None:
    sink = InvalidEventSink()

    assert not isinstance(sink, EventSink)
