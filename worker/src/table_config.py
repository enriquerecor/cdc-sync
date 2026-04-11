import json
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path


@dataclass(frozen=True)
class TableSourceConfig:
    adapter: str
    table: str
    topic: str
    connection: str
    schema: str | None = None


@dataclass(frozen=True)
class TableSyncConfig:
    mode: str


@dataclass(frozen=True)
class TableConfig:
    enabled: bool
    source: TableSourceConfig
    primary_key_fields: tuple[str, ...]
    sync: TableSyncConfig


@dataclass(frozen=True)
class TableRegistryConfig:
    version: int
    tables: dict[str, TableConfig]


def load_table_registry(path: str) -> TableRegistryConfig:
    root_config = _expect_dict(_read_json_file(path), "La configuracion de tablas")
    raw_tables = _expect_dict(root_config["tables"], "La clave 'tables'")

    return TableRegistryConfig(
        version=_expect_int(root_config["version"], "La clave 'version'"),
        tables={
            _expect_str(logical_name, "El nombre logico de la tabla"): _build_table_config(
                logical_name, raw_table
            )
            for logical_name, raw_table in raw_tables.items()
        },
    )


def _read_json_file(path: str) -> object:
    resolved_path = _resolve_config_path(path)

    try:
        with resolved_path.open(encoding="utf-8") as config_file:
            return json.load(config_file)
    except FileNotFoundError as exc:
        raise ValueError(
            f"No existe el fichero de configuracion de tablas: {path}"
        ) from exc
    except JSONDecodeError as exc:
        raise ValueError(
            f"El fichero de configuracion de tablas no es JSON valido: {path}"
        ) from exc


def _resolve_config_path(path: str) -> Path:
    config_path = Path(path)
    if config_path.is_absolute() or config_path.exists():
        return config_path

    worker_root = Path(__file__).resolve().parent.parent
    return worker_root / config_path


def _build_table_config(logical_name: object, raw_table: object) -> TableConfig:
    table_name = _expect_str(logical_name, "El nombre logico de la tabla")
    table_config = _expect_dict(raw_table, f"La tabla '{table_name}'")
    source_config = _expect_dict(
        table_config["source"], f"La tabla '{table_name}'.source"
    )
    sync_config = _expect_dict(table_config["sync"], f"La tabla '{table_name}'.sync")

    return TableConfig(
        enabled=_expect_bool(
            table_config["enabled"], f"La tabla '{table_name}'.enabled"
        ),
        source=TableSourceConfig(
            adapter=_expect_str(
                source_config["adapter"], f"La tabla '{table_name}'.source.adapter"
            ),
            table=_expect_str(
                source_config["table"], f"La tabla '{table_name}'.source.table"
            ),
            topic=_expect_str(
                source_config["topic"], f"La tabla '{table_name}'.source.topic"
            ),
            connection=_expect_str(
                source_config["connection"],
                f"La tabla '{table_name}'.source.connection",
            ),
            schema=_expect_optional_str(
                source_config.get("schema"),
                f"La tabla '{table_name}'.source.schema",
            ),
        ),
        primary_key_fields=tuple(
            _expect_str(field_name, f"La tabla '{table_name}'.pk[]")
            for field_name in _expect_list(
                table_config["pk"], f"La tabla '{table_name}'.pk"
            )
        ),
        sync=TableSyncConfig(
            mode=_expect_str(
                sync_config["mode"], f"La tabla '{table_name}'.sync.mode"
            )
        ),
    )


def _expect_dict(value: object, label: str) -> dict[object, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} debe ser un objeto JSON")

    return value


def _expect_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{label} debe ser una lista")

    return value


def _expect_str(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} debe ser una cadena")

    return value


def _expect_optional_str(value: object, label: str) -> str | None:
    if value is None:
        return None

    return _expect_str(value, label)


def _expect_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{label} debe ser booleano")

    return value


def _expect_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{label} debe ser un entero")

    return value
