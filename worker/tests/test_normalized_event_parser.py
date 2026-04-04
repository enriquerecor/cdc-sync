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
    assert event.deleted is False
    assert event.operation is Operation.SNAPSHOT


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
