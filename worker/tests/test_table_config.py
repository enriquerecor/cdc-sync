import json
from pathlib import Path

import pytest

from table_config import load_table_registry


def test_load_table_registry(tmp_path: Path) -> None:
    config_path = _write_temp_config(
        tmp_path,
        {
            "version": 1,
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
                }
            },
        },
    )

    registry = load_table_registry(str(config_path))

    assert registry.version == 1
    assert tuple(registry.tables) == ("customers",)
    assert registry.tables["customers"].source.adapter == "debezium_postgres"
    assert registry.tables["customers"].primary_key_fields == ("id",)


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


def _write_temp_config(tmp_path: Path, content: dict[str, object]) -> Path:
    config_path = tmp_path / "tables.json"
    config_path.write_text(json.dumps(content), encoding="utf-8")
    return config_path
