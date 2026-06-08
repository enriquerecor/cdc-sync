from dataclasses import dataclass


@dataclass(frozen=True)
class TableSourceConfig:
    adapter: str
    schema: str
    table: str
    topic: str


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


def build_table_configs_from_runtime(raw_tables: object) -> dict[str, TableConfig]:
    tables_config = _expect_dict(raw_tables, "La clave 'tables'")
    tables = {
        _expect_non_empty_str(
            logical_name,
            "El nombre lógico de la tabla",
        ): _build_table_config(logical_name, raw_table)
        for logical_name, raw_table in tables_config.items()
    }
    _validate_destination_tables(tables)

    return tables


def _build_table_config(logical_name: object, raw_table: object) -> TableConfig:
    table_name = _expect_non_empty_str(logical_name, "El nombre lógico de la tabla")
    table_config = _expect_dict(raw_table, f"La tabla '{table_name}'")
    source_config = _expect_dict(
        _required_value(table_config, "source", f"La tabla '{table_name}'"),
        f"La tabla '{table_name}'.source",
    )
    sync_config = _expect_dict(
        _required_value(table_config, "sync", f"La tabla '{table_name}'"),
        f"La tabla '{table_name}'.sync",
    )
    destination_config = _expect_dict(
        _required_value(table_config, "destination", f"La tabla '{table_name}'"),
        f"La tabla '{table_name}'.destination",
    )
    primary_key_fields = tuple(
        _expect_non_empty_str(field_name, f"La tabla '{table_name}'.pk[]")
        for field_name in _expect_list(
            _required_value(table_config, "pk", f"La tabla '{table_name}'"),
            f"La tabla '{table_name}'.pk",
        )
    )
    destination = _build_destination_config(table_name, destination_config)
    _validate_table_destination(table_name, primary_key_fields, destination)

    return TableConfig(
        enabled=_expect_bool(
            _required_value(table_config, "enabled", f"La tabla '{table_name}'"),
            f"La tabla '{table_name}'.enabled",
        ),
        source=TableSourceConfig(
            adapter=_expect_non_empty_str(
                _required_value(
                    source_config,
                    "adapter",
                    f"La tabla '{table_name}'.source",
                ),
                f"La tabla '{table_name}'.source.adapter",
            ),
            schema=_expect_non_empty_str(
                _required_value(
                    source_config,
                    "schema",
                    f"La tabla '{table_name}'.source",
                ),
                f"La tabla '{table_name}'.source.schema",
            ),
            table=_expect_non_empty_str(
                _required_value(
                    source_config,
                    "table",
                    f"La tabla '{table_name}'.source",
                ),
                f"La tabla '{table_name}'.source.table",
            ),
            topic=_expect_non_empty_str(
                _required_value(
                    source_config,
                    "topic",
                    f"La tabla '{table_name}'.source",
                ),
                f"La tabla '{table_name}'.source.topic",
            ),
        ),
        primary_key_fields=primary_key_fields,
        sync=TableSyncConfig(
            mode=_expect_non_empty_str(
                _required_value(sync_config, "mode", f"La tabla '{table_name}'.sync"),
                f"La tabla '{table_name}'.sync.mode",
            )
        ),
        destination=destination,
    )


def _build_destination_config(
    table_name: str,
    destination_config: dict[object, object],
) -> TableDestinationConfig:
    raw_columns = _expect_list(
        _required_value(
            destination_config,
            "columns",
            f"La tabla '{table_name}'.destination",
        ),
        f"La tabla '{table_name}'.destination.columns",
    )

    return TableDestinationConfig(
        table=_expect_non_empty_str(
            _required_value(
                destination_config,
                "table",
                f"La tabla '{table_name}'.destination",
            ),
            f"La tabla '{table_name}'.destination.table",
        ),
        columns=tuple(
            _build_destination_column_config(table_name, index, raw_column)
            for index, raw_column in enumerate(raw_columns)
        ),
    )


def _build_destination_column_config(
    table_name: str,
    index: int,
    raw_column: object,
) -> TableDestinationColumnConfig:
    label = f"La tabla '{table_name}'.destination.columns[{index}]"
    column_config = _expect_dict(raw_column, label)

    return TableDestinationColumnConfig(
        name=_expect_non_empty_str(
            _required_value(column_config, "name", label),
            f"{label}.name",
        ),
        type=_expect_non_empty_str(
            _required_value(column_config, "type", label),
            f"{label}.type",
        ),
        nullable=_expect_bool(
            _required_value(column_config, "nullable", label),
            f"{label}.nullable",
        ),
    )


def _validate_table_destination(
    table_name: str,
    primary_key_fields: tuple[str, ...],
    destination: TableDestinationConfig,
) -> None:
    if not primary_key_fields:
        raise ValueError(f"La tabla '{table_name}'.pk debe incluir al menos una columna")

    if not destination.columns:
        raise ValueError(
            f"La tabla '{table_name}'.destination.columns debe incluir al menos una columna"
        )

    destination_columns_by_name: dict[str, TableDestinationColumnConfig] = {}
    for column in destination.columns:
        if column.name in {"version", "deleted"}:
            raise ValueError(
                f"La tabla '{table_name}'.destination.columns no puede declarar la columna técnica '{column.name}'"
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
                f"La tabla de destino '{destination_table}' está duplicada para "
                f"'{conflicting_table_name}' y '{logical_table_name}'"
            )

        destination_tables[destination_table] = logical_table_name


def _required_value(
    value: dict[object, object],
    key: str,
    label: str,
) -> object:
    try:
        return value[key]
    except KeyError as exc:
        raise ValueError(f"{label}.{key} es obligatorio") from exc


def _expect_dict(value: object, label: str) -> dict[object, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} debe ser un objeto JSON")

    return value


def _expect_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{label} debe ser una lista")

    return value


def _expect_non_empty_str(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} debe ser una cadena")

    normalized_value = value.strip()
    if normalized_value:
        return normalized_value

    raise ValueError(f"{label} no puede estar vacío")


def _expect_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{label} debe ser booleano")

    return value
