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
class TableDestinationColumnConfig:
    name: str
    type: str
    nullable: bool


@dataclass(frozen=True)
class TableDestinationConfig:
    table: str
    columns: tuple[TableDestinationColumnConfig, ...]


@dataclass(frozen=True)
class TableConfig:
    enabled: bool
    source: TableSourceConfig
    primary_key_fields: tuple[str, ...]
    sync: TableSyncConfig
    destination: TableDestinationConfig


@dataclass(frozen=True)
class TableRegistryConfig:
    version: int
    tables: dict[str, TableConfig]


def load_table_registry(path: str) -> TableRegistryConfig:
    root_config = _expect_dict(_read_json_file(path), "La configuracion de tablas")
    raw_tables = _expect_dict(root_config["tables"], "La clave 'tables'")
    tables = {
        _expect_str(logical_name, "El nombre logico de la tabla"): _build_table_config(
            logical_name, raw_table
        )
        for logical_name, raw_table in raw_tables.items()
    }
    _validate_destination_tables(tables)

    return TableRegistryConfig(
        version=_expect_int(root_config["version"], "La clave 'version'"),
        tables=tables,
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
    destination_config = _expect_dict(
        table_config["destination"], f"La tabla '{table_name}'.destination"
    )
    primary_key_fields = tuple(
        _expect_str(field_name, f"La tabla '{table_name}'.pk[]")
        for field_name in _expect_list(table_config["pk"], f"La tabla '{table_name}'.pk")
    )
    destination = _build_destination_config(table_name, destination_config)
    _validate_table_destination(table_name, primary_key_fields, destination)

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
        primary_key_fields=primary_key_fields,
        sync=TableSyncConfig(
            mode=_expect_str(
                sync_config["mode"], f"La tabla '{table_name}'.sync.mode"
            )
        ),
        destination=destination,
    )


def _build_destination_config(
    table_name: str,
    destination_config: dict[object, object],
) -> TableDestinationConfig:
    default_nullable = _expect_optional_bool(
        destination_config.get("default_nullable"),
        f"La tabla '{table_name}'.destination.default_nullable",
    )
    raw_columns = _expect_list(
        destination_config["columns"],
        f"La tabla '{table_name}'.destination.columns",
    )

    return TableDestinationConfig(
        table=_expect_str(
            destination_config["table"],
            f"La tabla '{table_name}'.destination.table",
        ),
        columns=tuple(
            _build_destination_column_config(
                table_name,
                index,
                raw_column,
                default_nullable=default_nullable,
            )
            for index, raw_column in enumerate(raw_columns)
        ),
    )


def _build_destination_column_config(
    table_name: str,
    index: int,
    raw_column: object,
    *,
    default_nullable: bool | None,
) -> TableDestinationColumnConfig:
    label = f"La tabla '{table_name}'.destination.columns[{index}]"
    column_config = _expect_dict(raw_column, label)
    column_nullable = _expect_optional_bool(
        column_config.get("nullable"),
        f"{label}.nullable",
    )

    return TableDestinationColumnConfig(
        name=_expect_str(column_config["name"], f"{label}.name"),
        type=_expect_str(column_config["type"], f"{label}.type"),
        nullable=_resolve_destination_column_nullable(
            column_nullable=column_nullable,
            default_nullable=default_nullable,
        ),
    )


def _validate_table_destination(
    table_name: str,
    primary_key_fields: tuple[str, ...],
    destination: TableDestinationConfig,
) -> None:
    if not primary_key_fields:
        raise ValueError(
            f"La tabla '{table_name}'.pk debe incluir al menos una columna"
        )

    if not destination.columns:
        raise ValueError(
            f"La tabla '{table_name}'.destination.columns debe incluir al menos una columna"
        )

    destination_columns_by_name: dict[str, TableDestinationColumnConfig] = {}
    for column in destination.columns:
        if column.name in {"version", "deleted"}:
            raise ValueError(
                f"La tabla '{table_name}'.destination.columns no puede declarar la columna tecnica '{column.name}'"
            )

        if column.name in destination_columns_by_name:
            raise ValueError(
                f"La tabla '{table_name}'.destination.columns tiene la columna duplicada '{column.name}'"
            )

        destination_columns_by_name[column.name] = column

    for primary_key_field in primary_key_fields:
        try:
            column = destination_columns_by_name[primary_key_field]
        except KeyError as exc:
            raise ValueError(
                f"La tabla '{table_name}'.destination.columns debe incluir la columna de PK '{primary_key_field}'"
            ) from exc

        if column.nullable:
            raise ValueError(
                f"La tabla '{table_name}'.destination.columns marca la PK '{primary_key_field}' como nullable"
            )


def _validate_destination_tables(tables: dict[str, TableConfig]) -> None:
    destination_tables: dict[str, str] = {}

    for logical_table_name, table_config in tables.items():
        destination_table = table_config.destination.table
        conflicting_table_name = destination_tables.get(destination_table)
        if conflicting_table_name is not None:
            raise ValueError(
                f"La tabla de destino '{destination_table}' esta duplicada para "
                f"'{conflicting_table_name}' y '{logical_table_name}'"
            )

        destination_tables[destination_table] = logical_table_name


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


def _expect_optional_bool(value: object, label: str) -> bool | None:
    if value is None:
        return None

    return _expect_bool(value, label)


def _expect_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{label} debe ser un entero")

    return value


def _resolve_destination_column_nullable(
    *,
    column_nullable: bool | None,
    default_nullable: bool | None,
) -> bool:
    if column_nullable is not None:
        return column_nullable

    if default_nullable is not None:
        return default_nullable

    return False
