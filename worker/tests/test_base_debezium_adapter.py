from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from adapters.base_debezium_adapter import BaseDebeziumAdapter
from normalized_event import Operation

from .helpers import build_debezium_event


class FakeDebeziumAdapter(BaseDebeziumAdapter):
    def extract_version(self, value: dict[str, object]) -> int:
        return 1

    def extract_source_position(self, value: dict[str, object]) -> dict[str, object]:
        return {"offset": 1}


def test_extract_table_name_uses_source_table() -> None:
    adapter = FakeDebeziumAdapter()

    table_name = adapter.extract_table_name(
        "cdc_sync.public.fallback",
        build_debezium_event(operation="c", table="customers", lsn=101),
    )

    assert table_name == "customers"


def test_extract_table_name_falls_back_to_topic() -> None:
    adapter = FakeDebeziumAdapter()

    table_name = adapter.extract_table_name(
        "cdc_sync.public.customers",
        {"payload": {"source": {}}},
    )

    assert table_name == "customers"


def test_extract_operation_maps_debezium_codes() -> None:
    adapter = FakeDebeziumAdapter()

    operation = adapter.extract_operation(
        build_debezium_event(operation="r", table="customers", lsn=101)
    )

    assert operation is Operation.SNAPSHOT


def test_extract_data_uses_before_for_delete() -> None:
    adapter = FakeDebeziumAdapter()

    data = adapter.extract_data(
        build_debezium_event(
            operation="d",
            table="orders",
            lsn=202,
            before={"id": 3, "status": "cancelled"},
        ),
        Operation.DELETE,
    )

    assert data == {"id": 3, "status": "cancelled"}


def test_extract_operation_fails_for_unsupported_code() -> None:
    adapter = FakeDebeziumAdapter()

    with pytest.raises(ValueError, match="Operacion de Debezium no soportada: x"):
        adapter.extract_operation({"payload": {"op": "x"}})


def test_extract_data_normalizes_debezium_logical_types() -> None:
    adapter = FakeDebeziumAdapter()

    data = adapter.extract_data(
        build_debezium_event(
            operation="c",
            table="orders",
            lsn=303,
            after={
                "id": 3,
                "total_amount": "EYo=",
                "created_at": "2026-04-11T18:29:50.264373Z",
            },
            after_schema_fields=[
                {"type": "int64", "field": "id"},
                {
                    "type": "bytes",
                    "name": "org.apache.kafka.connect.data.Decimal",
                    "parameters": {"scale": "2"},
                    "field": "total_amount",
                },
                {
                    "type": "string",
                    "name": "io.debezium.time.ZonedTimestamp",
                    "field": "created_at",
                },
            ],
        ),
        Operation.INSERT,
    )

    assert data == {
        "id": 3,
        "total_amount": Decimal("44.90"),
        "created_at": datetime(
            2026,
            4,
            11,
            18,
            29,
            50,
            264373,
            tzinfo=timezone.utc,
        ),
    }


def test_extract_data_fails_when_schema_is_missing_field() -> None:
    adapter = FakeDebeziumAdapter()

    with pytest.raises(
        ValueError,
        match="El schema de Debezium no incluye el campo 'total_amount'",
    ):
        adapter.extract_data(
            build_debezium_event(
                operation="c",
                table="orders",
                lsn=404,
                after={"id": 3, "total_amount": "EYo="},
                after_schema_fields=[
                    {"type": "int64", "field": "id"},
                ],
            ),
            Operation.INSERT,
        )


def test_extract_data_normalizes_boolean_date_timestamp_uuid_json_and_bytes() -> None:
    adapter = FakeDebeziumAdapter()

    data = adapter.extract_data(
        build_debezium_event(
            operation="c",
            table="customers",
            lsn=505,
            after={
                "is_active": 1,
                "birth_date": 20554,
                "updated_at": 1775932190265,
                "external_id": "550e8400-e29b-41d4-a716-446655440000",
                "metadata": '{"tier":"gold","flags":[true,false]}',
                "attachment": "YWJj",
            },
            after_schema_fields=[
                {"type": "boolean", "field": "is_active"},
                {
                    "type": "int32",
                    "name": "io.debezium.time.Date",
                    "field": "birth_date",
                },
                {
                    "type": "int64",
                    "name": "io.debezium.time.Timestamp",
                    "field": "updated_at",
                },
                {
                    "type": "string",
                    "name": "io.debezium.data.Uuid",
                    "field": "external_id",
                },
                {
                    "type": "string",
                    "name": "io.debezium.data.Json",
                    "field": "metadata",
                },
                {"type": "bytes", "field": "attachment"},
            ],
        ),
        Operation.INSERT,
    )

    assert data == {
        "is_active": True,
        "birth_date": date(2026, 4, 11),
        "updated_at": datetime(2026, 4, 11, 18, 29, 50, 265000),
        "external_id": "550e8400-e29b-41d4-a716-446655440000",
        "metadata": {"tier": "gold", "flags": [True, False]},
        "attachment": b"abc",
    }
