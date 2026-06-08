from copy import deepcopy

import pytest

from table_config import build_table_configs_from_runtime


def test_build_table_configs_from_runtime() -> None:
    tables = build_table_configs_from_runtime(_runtime_tables())

    assert tuple(tables) == ("customers",)
    assert tables["customers"].enabled is True
    assert tables["customers"].source.adapter == "debezium_postgres"
    assert tables["customers"].source.schema == "public"
    assert tables["customers"].source.table == "customers"
    assert tables["customers"].source.topic == "cdc_sync.public.customers"
    assert tables["customers"].primary_key_fields == ("id",)
    assert tables["customers"].destination.table == "customers"
    assert tables["customers"].destination.columns[1].name == "email"
    assert tables["customers"].destination.columns[1].nullable is True


def test_build_table_configs_does_not_require_source_connection() -> None:
    tables = build_table_configs_from_runtime(_runtime_tables())

    assert not hasattr(tables["customers"].source, "connection")


def test_build_table_configs_fails_with_invalid_structure() -> None:
    with pytest.raises(TypeError, match="La clave 'tables' debe ser un objeto JSON"):
        build_table_configs_from_runtime([])


def test_build_table_configs_fails_when_pk_is_missing_from_destination() -> None:
    runtime_tables = _runtime_tables()
    runtime_tables["customers"]["destination"]["columns"] = [
        {"name": "email", "type": "String", "nullable": True}
    ]

    with pytest.raises(
        ValueError,
        match="La tabla 'customers'.destination.columns debe incluir la columna de PK 'id'",
    ):
        build_table_configs_from_runtime(runtime_tables)


def test_build_table_configs_fails_when_pk_is_nullable_in_destination() -> None:
    runtime_tables = _runtime_tables()
    runtime_tables["customers"]["destination"]["columns"] = [
        {"name": "id", "type": "UInt64", "nullable": True}
    ]

    with pytest.raises(
        ValueError,
        match="La tabla 'customers'.destination.columns marca la PK 'id' como nullable",
    ):
        build_table_configs_from_runtime(runtime_tables)


def test_build_table_configs_fails_when_destination_column_is_technical() -> None:
    runtime_tables = _runtime_tables()
    runtime_tables["customers"]["destination"]["columns"].append(
        {"name": "version", "type": "UInt64", "nullable": False}
    )

    with pytest.raises(
        ValueError,
        match="La tabla 'customers'.destination.columns no puede declarar la columna técnica 'version'",
    ):
        build_table_configs_from_runtime(runtime_tables)


def test_build_table_configs_fails_when_destination_table_is_duplicated() -> None:
    runtime_tables = _runtime_tables()
    runtime_tables["orders"] = deepcopy(runtime_tables["customers"])
    runtime_tables["orders"]["source"]["table"] = "orders"
    runtime_tables["orders"]["source"]["topic"] = "cdc_sync.public.orders"

    with pytest.raises(
        ValueError,
        match="La tabla de destino 'customers' está duplicada para 'customers' y 'orders'",
    ):
        build_table_configs_from_runtime(runtime_tables)


def test_build_table_configs_fails_without_column_nullable() -> None:
    runtime_tables = _runtime_tables()
    del runtime_tables["customers"]["destination"]["columns"][1]["nullable"]

    with pytest.raises(
        ValueError,
        match="La tabla 'customers'.destination.columns\\[1\\].nullable es obligatorio",
    ):
        build_table_configs_from_runtime(runtime_tables)


def _runtime_tables() -> dict[str, object]:
    return deepcopy(
        {
            "customers": {
                "enabled": True,
                "source": {
                    "adapter": "debezium_postgres",
                    "schema": "public",
                    "table": "customers",
                    "topic": "cdc_sync.public.customers",
                },
                "pk": ["id"],
                "sync": {"mode": "realtime"},
                "destination": {
                    "table": "customers",
                    "columns": [
                        {"name": "id", "type": "UInt64", "nullable": False},
                        {"name": "email", "type": "String", "nullable": True},
                    ],
                },
            }
        }
    )
