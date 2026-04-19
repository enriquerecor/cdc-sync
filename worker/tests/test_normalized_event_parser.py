from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from adapters.registry import build_change_event_adapters
from normalized_event import Operation
from normalized_event_parser import NormalizedEventParser

from .helpers import build_debezium_event, build_table_config


def test_parse_insert_event(parser: NormalizedEventParser) -> None:
    event = parser.parse(
        "cdc_sync.public.customers",
        build_debezium_event(
            operation="c",
            table="customers",
            lsn=101,
            after={"id": 1, "email": "insert@example.com"},
        ),
    )

    assert event is not None
    assert event.table == "customers"
    assert event.primary_key == {"id": 1}
    assert event.data == {"id": 1, "email": "insert@example.com"}
    assert event.version == 101
    assert event.source_position == {"lsn": 101}
    assert event.deleted is False
    assert event.operation is Operation.INSERT


def test_parse_update_event(parser: NormalizedEventParser) -> None:
    event = parser.parse(
        "cdc_sync.public.customers",
        build_debezium_event(
            operation="u",
            table="customers",
            lsn=202,
            after={"id": 2, "email": "update@example.com"},
        ),
    )

    assert event is not None
    assert event.primary_key == {"id": 2}
    assert event.data == {"id": 2, "email": "update@example.com"}
    assert event.version == 202
    assert event.source_position == {"lsn": 202}
    assert event.deleted is False
    assert event.operation is Operation.UPDATE


def test_parse_delete_event_uses_before_snapshot(
    parser: NormalizedEventParser,
) -> None:
    event = parser.parse(
        "cdc_sync.public.orders",
        build_debezium_event(
            operation="d",
            table="orders",
            lsn=303,
            before={"id": 3, "status": "cancelled"},
        ),
    )

    assert event is not None
    assert event.table == "orders"
    assert event.primary_key == {"id": 3}
    assert event.data == {}
    assert event.version == 303
    assert event.source_position == {"lsn": 303}
    assert event.deleted is True
    assert event.operation is Operation.DELETE


def test_parse_snapshot_event(parser: NormalizedEventParser) -> None:
    event = parser.parse(
        "cdc_sync.public.customers",
        build_debezium_event(
            operation="r",
            table="customers",
            lsn=404,
            after={"id": 4, "email": "snapshot@example.com"},
        ),
    )

    assert event is not None
    assert event.primary_key == {"id": 4}
    assert event.data == {"id": 4, "email": "snapshot@example.com"}
    assert event.version == 404
    assert event.source_position == {"lsn": 404}
    assert event.deleted is False
    assert event.operation is Operation.SNAPSHOT


def test_parse_normalizes_debezium_logical_types(parser: NormalizedEventParser) -> None:
    event = parser.parse(
        "cdc_sync.public.orders",
        build_debezium_event(
            operation="c",
            table="orders",
            lsn=505,
            after={
                "id": 3,
                "customer_id": 7,
                "order_number": "ORD-3",
                "total_amount": "EYo=",
                "status": "created",
                "created_at": "2026-04-11T18:29:50.264373Z",
            },
            after_schema_fields=[
                {"type": "int64", "field": "id"},
                {"type": "int64", "field": "customer_id"},
                {"type": "string", "field": "order_number"},
                {
                    "type": "bytes",
                    "name": "org.apache.kafka.connect.data.Decimal",
                    "parameters": {"scale": "2"},
                    "field": "total_amount",
                },
                {"type": "string", "field": "status"},
                {
                    "type": "string",
                    "name": "io.debezium.time.ZonedTimestamp",
                    "field": "created_at",
                },
            ],
        ),
    )

    assert event is not None
    assert event.primary_key == {"id": 3}
    assert event.data == {
        "id": 3,
        "customer_id": 7,
        "order_number": "ORD-3",
        "total_amount": Decimal("44.90"),
        "status": "created",
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
    assert event.version == 505


def test_parse_supports_extended_normalized_types(parser: NormalizedEventParser) -> None:
    event = parser.parse(
        "cdc_sync.public.customers",
        build_debezium_event(
            operation="c",
            table="customers",
            lsn=606,
            after={
                "id": 9,
                "email": "typed@example.com",
                "is_active": True,
                "birth_date": "2026-04-11",
                "updated_at": "2026-04-11T20:10:11",
                "external_id": "550e8400-e29b-41d4-a716-446655440000",
                "metadata": '{"source":"erp","enabled":true}',
                "attachment": "YWJj",
            },
            after_schema_fields=[
                {"type": "int64", "field": "id"},
                {"type": "string", "field": "email"},
                {"type": "boolean", "field": "is_active"},
                {
                    "type": "string",
                    "name": "io.debezium.time.IsoDate",
                    "field": "birth_date",
                },
                {
                    "type": "string",
                    "name": "io.debezium.time.IsoTimestamp",
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
    )

    assert event is not None
    assert event.primary_key == {"id": 9}
    assert event.data == {
        "id": 9,
        "email": "typed@example.com",
        "is_active": True,
        "birth_date": date(2026, 4, 11),
        "updated_at": datetime(2026, 4, 11, 20, 10, 11),
        "external_id": "550e8400-e29b-41d4-a716-446655440000",
        "metadata": {"source": "erp", "enabled": True},
        "attachment": b"abc",
    }


def test_parse_fails_when_adapter_returns_value_outside_normalized_contract() -> None:
    class InvalidAdapter:
        def is_tombstone(self, value: object) -> bool:
            return False

        def extract_table_name(self, topic: str, value: dict[str, object]) -> str:
            return "customers"

        def extract_operation(self, value: dict[str, object]) -> Operation:
            return Operation.INSERT

        def extract_data(
            self,
            value: dict[str, object],
            operation: Operation,
        ) -> dict[str, object]:
            return {"id": 1, "invalid": {1, 2, 3}}

        def extract_version(self, value: dict[str, object]) -> int:
            return 1

        def extract_source_position(self, value: dict[str, object]) -> dict[str, object]:
            return {"offset": 1}

    parser = NormalizedEventParser(
        adapters={"invalid": InvalidAdapter()},
        tables={
            "customers": build_table_config(
                table="customers",
                topic="cdc_sync.public.customers",
                primary_key_fields=("id",),
                adapter="invalid",
            )
        },
    )

    with pytest.raises(
        TypeError,
        match="no pertenece al contrato interno de tipos normalizados",
    ):
        parser.parse("cdc_sync.public.customers", {"payload": {}})


def test_parse_tombstone_returns_none(parser: NormalizedEventParser) -> None:
    event = parser.parse("cdc_sync.public.customers", None)

    assert event is None


def test_parse_fails_when_table_is_not_declared(
    parser: NormalizedEventParser,
) -> None:
    with pytest.raises(
        ValueError, match="El topic 'cdc_sync.public.unknown' no existe en la configuracion"
    ):
        parser.parse(
            "cdc_sync.public.unknown",
            build_debezium_event(
                operation="c",
                table="unknown",
                lsn=505,
                after={"id": 5},
            ),
        )


def test_parse_fails_when_primary_key_field_is_missing(
    parser: NormalizedEventParser,
) -> None:
    with pytest.raises(
        ValueError,
        match="Falta el campo de PK 'id' en los datos de la tabla 'customers'",
    ):
        parser.parse(
            "cdc_sync.public.customers",
            build_debezium_event(
                operation="c",
                table="customers",
                lsn=606,
                after={"email": "missing-pk@example.com"},
            ),
        )


def test_parse_fails_when_destination_column_is_missing_in_upsert() -> None:
    parser = NormalizedEventParser(
        adapters=build_change_event_adapters(),
        tables={
            "customers": build_table_config(
                table="customers",
                topic="cdc_sync.public.customers",
                primary_key_fields=("id",),
                destination_columns=(
                    ("id", "UInt64", False),
                    ("email", "String", True),
                ),
            )
        },
    )

    with pytest.raises(
        ValueError,
        match="no incluye la columna configurada 'email'",
    ):
        parser.parse(
            "cdc_sync.public.customers",
            build_debezium_event(
                operation="u",
                table="customers",
                lsn=607,
                after={"id": 7},
            ),
        )


def test_parse_fails_when_lsn_is_missing(parser: NormalizedEventParser) -> None:
    with pytest.raises(
        ValueError,
        match="El payload de Debezium PostgreSQL debe incluir 'source.lsn' como entero",
    ):
        parser.parse(
            "cdc_sync.public.customers",
            build_debezium_event(
                operation="c",
                table="customers",
                lsn=None,
                after={"id": 7, "email": "missing-lsn@example.com"},
            ),
        )


def test_parse_delete_does_not_require_non_pk_columns() -> None:
    parser = NormalizedEventParser(
        adapters=build_change_event_adapters(),
        tables={
            "orders": build_table_config(
                table="orders",
                topic="cdc_sync.public.orders",
                primary_key_fields=("id",),
                destination_columns=(
                    ("id", "UInt64", False),
                    ("status", "String", False),
                ),
            )
        },
    )

    event = parser.parse(
        "cdc_sync.public.orders",
        build_debezium_event(
            operation="d",
            table="orders",
            lsn=808,
            before={"id": 8},
        ),
    )

    assert event is not None
    assert event.primary_key == {"id": 8}
    assert event.data == {}
    assert event.deleted is True


def test_parser_fails_at_startup_when_adapter_is_not_registered() -> None:
    with pytest.raises(
        ValueError,
        match="El adapter 'unknown_adapter' no existe en la configuracion del worker para la tabla 'customers'",
    ):
        NormalizedEventParser(
            adapters={},
            tables={
                "customers": build_table_config(
                    table="customers",
                    topic="cdc_sync.public.customers",
                    primary_key_fields=("id",),
                    adapter="unknown_adapter",
                )
            },
        )


def test_parser_fails_at_startup_when_topic_is_duplicated() -> None:
    with pytest.raises(
        ValueError,
        match="El topic 'cdc_sync.public.shared' esta duplicado en la configuracion para las tablas 'customers' y 'orders'",
    ):
        NormalizedEventParser(
            adapters=build_change_event_adapters(),
            tables={
                "customers": build_table_config(
                    table="customers",
                    topic="cdc_sync.public.shared",
                    primary_key_fields=("id",),
                ),
                "orders": build_table_config(
                    table="orders",
                    topic="cdc_sync.public.shared",
                    primary_key_fields=("id",),
                ),
            },
        )


def test_parse_fails_when_payload_table_does_not_match_topic_config(
    parser: NormalizedEventParser,
) -> None:
    with pytest.raises(
        ValueError,
        match="El evento del topic 'cdc_sync.public.customers' se resolvio para la tabla 'orders', pero la configuracion del worker espera 'customers'",
    ):
        parser.parse(
            "cdc_sync.public.customers",
            build_debezium_event(
                operation="c",
                table="orders",
                lsn=808,
                after={"id": 8},
            ),
        )
