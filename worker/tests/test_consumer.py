from dataclasses import dataclass

import pytest

from config import WorkerConfig
from consumer import _deserialize_payload, _persist_records
from event_sink import EventSink
from normalized_event import NormalizedEvent
from normalized_event_parser import NormalizedEventParser

from .helpers import build_debezium_event, build_table_config


@dataclass(frozen=True)
class FakeRecord:
    topic: str
    partition: int
    offset: int
    value: object


@dataclass
class FakeEventSink(EventSink):
    persisted_events: list[NormalizedEvent]

    def persist(self, event: NormalizedEvent) -> None:
        self.persisted_events.append(event)


class FailingEventSink(EventSink):
    def persist(self, event: NormalizedEvent) -> None:
        raise RuntimeError("sink failure")


@pytest.fixture
def worker_config() -> WorkerConfig:
    return WorkerConfig(
        kafka_bootstrap_servers="kafka:29092",
        kafka_topics=["cdc_sync.public.customers"],
        kafka_client_id="cdc-sync-worker",
        kafka_group_id="cdc-sync-worker",
        kafka_auto_offset_reset="earliest",
        kafka_poll_timeout_ms=1000,
        table_config_path="config/tables.json",
        table_config_version=1,
        tables={
            "customers": build_table_config(
                table="customers",
                topic="cdc_sync.public.customers",
                primary_key_fields=("id",),
            )
        },
    )


def test_deserialize_payload_returns_json_object() -> None:
    payload = b'{"payload":{"op":"c"}}'

    decoded_payload = _deserialize_payload(payload)

    assert decoded_payload == {"payload": {"op": "c"}}


def test_deserialize_payload_fails_with_invalid_json() -> None:
    with pytest.raises(ValueError, match="El payload de Kafka no es JSON valido"):
        _deserialize_payload(b"{invalid json")


def test_persist_records_delegates_normalized_event_to_sink(
    worker_config: WorkerConfig,
    parser: NormalizedEventParser,
) -> None:
    sink = FakeEventSink(persisted_events=[])
    record = FakeRecord(
        topic="cdc_sync.public.customers",
        partition=0,
        offset=12,
        value=build_debezium_event(
            operation="c",
            table="customers",
            lsn=707,
            after={"id": 8, "email": "consumer-log@example.com"},
        ),
    )

    _persist_records(worker_config, parser, sink, {object(): [record]})

    assert len(sink.persisted_events) == 1
    assert sink.persisted_events[0].table == "customers"
    assert sink.persisted_events[0].operation.value == "insert"
    assert sink.persisted_events[0].version == 707
    assert sink.persisted_events[0].source_position == {"lsn": 707}
    assert sink.persisted_events[0].primary_key == {"id": 8}
    assert sink.persisted_events[0].data == {
        "id": 8,
        "email": "consumer-log@example.com",
    }


def test_persist_records_skips_tombstones(
    worker_config: WorkerConfig,
    parser: NormalizedEventParser,
) -> None:
    sink = FakeEventSink(persisted_events=[])
    record = FakeRecord(
        topic="cdc_sync.public.customers",
        partition=0,
        offset=13,
        value=None,
    )

    _persist_records(worker_config, parser, sink, {object(): [record]})

    assert sink.persisted_events == []


def test_persist_records_wraps_sink_errors_with_record_context(
    worker_config: WorkerConfig,
    parser: NormalizedEventParser,
) -> None:
    record = FakeRecord(
        topic="cdc_sync.public.customers",
        partition=2,
        offset=21,
        value=build_debezium_event(
            operation="c",
            table="customers",
            lsn=808,
            after={"id": 9, "email": "sink-error@example.com"},
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="No se pudo persistir el evento normalizado client_id=cdc-sync-worker topic=cdc_sync.public.customers partition=2 offset=21 table=customers operation=insert version=808 source_position=\\{'lsn': 808\\}",
    ):
        _persist_records(worker_config, parser, FailingEventSink(), {object(): [record]})
