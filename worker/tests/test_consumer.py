import logging
from dataclasses import dataclass

import pytest

from config import WorkerConfig
from consumer import _deserialize_payload, _log_records
from normalized_event_parser import NormalizedEventParser

from .helpers import build_debezium_event, build_table_config


@dataclass(frozen=True)
class FakeRecord:
    topic: str
    partition: int
    offset: int
    value: object


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


def test_log_records_logs_normalized_event(
    worker_config: WorkerConfig,
    parser: NormalizedEventParser,
    caplog: pytest.LogCaptureFixture,
) -> None:
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

    with caplog.at_level(logging.INFO):
        _log_records(worker_config, parser, {object(): [record]})

    assert len(caplog.messages) == 1
    assert "cdc_event client_id=cdc-sync-worker" in caplog.messages[0]
    assert "table=customers" in caplog.messages[0]
    assert "operation=insert" in caplog.messages[0]
    assert "version=707" in caplog.messages[0]
    assert "source_position={'lsn': 707}" in caplog.messages[0]
    assert "primary_key={'id': 8}" in caplog.messages[0]
    assert "data={'id': 8, 'email': 'consumer-log@example.com'}" in caplog.messages[0]
    assert "value=" not in caplog.messages[0]


def test_log_records_skips_tombstones(
    worker_config: WorkerConfig,
    parser: NormalizedEventParser,
    caplog: pytest.LogCaptureFixture,
) -> None:
    record = FakeRecord(
        topic="cdc_sync.public.customers",
        partition=0,
        offset=13,
        value=None,
    )

    with caplog.at_level(logging.INFO):
        _log_records(worker_config, parser, {object(): [record]})

    assert caplog.messages == []
