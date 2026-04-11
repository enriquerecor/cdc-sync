from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from clickhouse_event_sink import ClickHouseEventSink
from clickhouse_table_registry import build_clickhouse_table_registry
from config import ClickHouseConfig
from normalized_event import NormalizedEvent, Operation

from .helpers import build_table_config


@dataclass
class FakeClickHouseRowWriter:
    calls: list[tuple[str, list[dict[str, object]]]]

    def insert_rows(self, query: str, rows: list[dict[str, object]]) -> None:
        self.calls.append((query, rows))


def test_persist_insert_writes_versioned_row() -> None:
    sink = _build_sink(
        build_table_config(
            table="customers",
            topic="cdc_sync.public.customers",
            primary_key_fields=("id",),
            destination_columns=(
                ("id", "UInt64", False),
                ("email", "String", True),
                ("full_name", "String", True),
                ("created_at", "DateTime64(3, 'UTC')", True),
            ),
        )
    )
    event = NormalizedEvent(
        table="customers",
        primary_key={"id": 7},
        data={
            "id": 7,
            "email": "alice@example.com",
            "full_name": "Alice",
            "created_at": datetime(
                2026,
                4,
                11,
                18,
                29,
                44,
                513665,
                tzinfo=timezone.utc,
            ),
        },
        version=101,
        source_position={"lsn": 101},
        deleted=False,
        operation=Operation.INSERT,
    )

    sink.persist(event)

    query, rows = sink.row_writer.calls[0]
    assert "INSERT INTO `cdc_sync_analytics`.`customers`" in query
    assert rows == [
        {
            "id": 7,
            "email": "alice@example.com",
            "full_name": "Alice",
            "created_at": datetime(
                2026,
                4,
                11,
                18,
                29,
                44,
                513665,
                tzinfo=timezone.utc,
            ),
            "version": 101,
            "deleted": 0,
        }
    ]


def test_persist_delete_writes_pk_and_nulls_for_non_pk_columns() -> None:
    sink = _build_sink(
        build_table_config(
            table="orders",
            topic="cdc_sync.public.orders",
            primary_key_fields=("id",),
            destination_columns=(
                ("id", "UInt64", False),
                ("status", "String", True),
                ("total_amount", "Decimal(10, 2)", True),
                ("created_at", "DateTime64(3, 'UTC')", True),
            ),
        )
    )
    event = NormalizedEvent(
        table="orders",
        primary_key={"id": 9},
        data={},
        version=202,
        source_position={"lsn": 202},
        deleted=True,
        operation=Operation.DELETE,
    )

    sink.persist(event)

    _, rows = sink.row_writer.calls[0]
    assert rows == [
        {
            "id": 9,
            "status": None,
            "total_amount": None,
            "created_at": None,
            "version": 202,
            "deleted": 1,
        }
    ]


def test_persist_keeps_multiple_versions_for_same_pk() -> None:
    sink = _build_sink(
        build_table_config(
            table="customers",
            topic="cdc_sync.public.customers",
            primary_key_fields=("id",),
            destination_columns=(
                ("id", "UInt64", False),
                ("email", "String", True),
            ),
        )
    )

    sink.persist(
        NormalizedEvent(
            table="customers",
            primary_key={"id": 7},
            data={"id": 7, "email": "new@example.com"},
            version=300,
            source_position={"lsn": 300},
            deleted=False,
            operation=Operation.UPDATE,
        )
    )
    sink.persist(
        NormalizedEvent(
            table="customers",
            primary_key={"id": 7},
            data={"id": 7, "email": "old@example.com"},
            version=250,
            source_position={"lsn": 250},
            deleted=False,
            operation=Operation.UPDATE,
        )
    )

    assert sink.row_writer.calls[0][1][0]["version"] == 300
    assert sink.row_writer.calls[1][1][0]["version"] == 250


def test_persist_writes_normalized_decimal_values() -> None:
    sink = _build_sink(
        build_table_config(
            table="orders",
            topic="cdc_sync.public.orders",
            primary_key_fields=("id",),
            destination_columns=(
                ("id", "UInt64", False),
                ("total_amount", "Decimal(10, 2)", True),
            ),
        )
    )
    event = NormalizedEvent(
        table="orders",
        primary_key={"id": 3},
        data={"id": 3, "total_amount": Decimal("44.90")},
        version=505,
        source_position={"lsn": 505},
        deleted=False,
        operation=Operation.INSERT,
    )

    sink.persist(event)

    _, rows = sink.row_writer.calls[0]
    assert rows == [
        {
            "id": 3,
            "total_amount": Decimal("44.90"),
            "version": 505,
            "deleted": 0,
        }
    ]


def _build_sink(table_config) -> ClickHouseEventSink:
    row_writer = FakeClickHouseRowWriter(calls=[])
    table_registry = build_clickhouse_table_registry(
        ClickHouseConfig(
            host="clickhouse",
            port=9000,
            database="cdc_sync_analytics",
            user="cdc_sync",
            password="cdc_sync",
        ),
        tables={table_config.destination.table: table_config},
    )

    return ClickHouseEventSink(
        row_writer=row_writer,
        table_registry=table_registry,
    )
