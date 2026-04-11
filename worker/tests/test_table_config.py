import json
from pathlib import Path

import pytest

from table_config import load_table_registry


def test_load_table_registry(tmp_path: Path) -> None:
    config_path = _write_temp_config(
        tmp_path,
        {
            "version": 2,
            "tables": {
                "customers": {
                    "enabled": True,
                    "source": {
                        "adapter": "debezium_postgres",
                        "connection": "postgres_local",
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
            },
        },
    )

    registry = load_table_registry(str(config_path))

    assert registry.version == 2
    assert tuple(registry.tables) == ("customers",)
    assert registry.tables["customers"].source.adapter == "debezium_postgres"
    assert registry.tables["customers"].primary_key_fields == ("id",)
    assert registry.tables["customers"].destination.table == "customers"
    assert registry.tables["customers"].destination.columns[1].name == "email"


def test_load_table_registry_fails_with_invalid_structure(
    tmp_path: Path,
) -> None:
    config_path = _write_temp_config(tmp_path, {"version": 1, "tables": []})

    with pytest.raises(TypeError, match="La clave 'tables' debe ser un objeto JSON"):
        load_table_registry(str(config_path))


def test_load_table_registry_fails_with_invalid_json(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "tables.json"
    config_path.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=f"El fichero de configuracion de tablas no es JSON valido: {config_path}",
    ):
        load_table_registry(str(config_path))


def test_load_table_registry_fails_when_pk_is_missing_from_destination(
    tmp_path: Path,
) -> None:
    config_path = _write_temp_config(
        tmp_path,
        {
            "version": 2,
            "tables": {
                "customers": {
                    "enabled": True,
                    "source": {
                        "adapter": "debezium_postgres",
                        "connection": "postgres_local",
                        "schema": "public",
                        "table": "customers",
                        "topic": "cdc_sync.public.customers",
                    },
                    "pk": ["id"],
                    "sync": {"mode": "realtime"},
                    "destination": {
                        "table": "customers",
                        "columns": [
                            {"name": "email", "type": "String", "nullable": True}
                        ],
                    },
                }
            },
        },
    )

    with pytest.raises(
        ValueError,
        match="La tabla 'customers'.destination.columns debe incluir la columna de PK 'id'",
    ):
        load_table_registry(str(config_path))


def test_load_table_registry_fails_when_pk_is_nullable_in_destination(
    tmp_path: Path,
) -> None:
    config_path = _write_temp_config(
        tmp_path,
        {
            "version": 2,
            "tables": {
                "customers": {
                    "enabled": True,
                    "source": {
                        "adapter": "debezium_postgres",
                        "connection": "postgres_local",
                        "schema": "public",
                        "table": "customers",
                        "topic": "cdc_sync.public.customers",
                    },
                    "pk": ["id"],
                    "sync": {"mode": "realtime"},
                    "destination": {
                        "table": "customers",
                        "columns": [
                            {"name": "id", "type": "UInt64", "nullable": True}
                        ],
                    },
                }
            },
        },
    )

    with pytest.raises(
        ValueError,
        match="La tabla 'customers'.destination.columns marca la PK 'id' como nullable",
    ):
        load_table_registry(str(config_path))


def test_load_table_registry_fails_when_destination_column_is_technical(
    tmp_path: Path,
) -> None:
    config_path = _write_temp_config(
        tmp_path,
        {
            "version": 2,
            "tables": {
                "customers": {
                    "enabled": True,
                    "source": {
                        "adapter": "debezium_postgres",
                        "connection": "postgres_local",
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
                            {"name": "version", "type": "UInt64", "nullable": False},
                        ],
                    },
                }
            },
        },
    )

    with pytest.raises(
        ValueError,
        match="La tabla 'customers'.destination.columns no puede declarar la columna tecnica 'version'",
    ):
        load_table_registry(str(config_path))


def test_load_table_registry_fails_when_destination_table_is_duplicated(
    tmp_path: Path,
) -> None:
    config_path = _write_temp_config(
        tmp_path,
        {
            "version": 2,
            "tables": {
                "customers": {
                    "enabled": True,
                    "source": {
                        "adapter": "debezium_postgres",
                        "connection": "postgres_local",
                        "schema": "public",
                        "table": "customers",
                        "topic": "cdc_sync.public.customers",
                    },
                    "pk": ["id"],
                    "sync": {"mode": "realtime"},
                    "destination": {
                        "table": "analytics_rows",
                        "columns": [
                            {"name": "id", "type": "UInt64", "nullable": False}
                        ],
                    },
                },
                "orders": {
                    "enabled": True,
                    "source": {
                        "adapter": "debezium_postgres",
                        "connection": "postgres_local",
                        "schema": "public",
                        "table": "orders",
                        "topic": "cdc_sync.public.orders",
                    },
                    "pk": ["id"],
                    "sync": {"mode": "realtime"},
                    "destination": {
                        "table": "analytics_rows",
                        "columns": [
                            {"name": "id", "type": "UInt64", "nullable": False}
                        ],
                    },
                },
            },
        },
    )

    with pytest.raises(
        ValueError,
        match="La tabla de destino 'analytics_rows' esta duplicada para 'customers' y 'orders'",
    ):
        load_table_registry(str(config_path))


def _write_temp_config(tmp_path: Path, content: dict[str, object]) -> Path:
    config_path = tmp_path / "tables.json"
    config_path.write_text(json.dumps(content), encoding="utf-8")
    return config_path
