from __future__ import annotations

from cdc_sync_api.application.dto.editing_config_dto import (
    EditingConfigDto,
    EditingTableDto,
)

SUPPORTED_SOURCE_ADAPTERS = frozenset({"debezium_postgres"})
SUPPORTED_SYNC_MODES = frozenset({"realtime"})
RESERVED_DESTINATION_COLUMNS = frozenset({"version", "deleted"})


class EditingConfigValidationError(ValueError):
    """La configuración en edición no cumple las reglas del MVP."""


def validate_editing_config(config: EditingConfigDto) -> None:
    _validate_source_connections(config)
    _validate_tables(config)


def _validate_source_connections(config: EditingConfigDto) -> None:
    seen_connection_names: set[str] = set()

    for source_connection in config.source_connections:
        if source_connection.name in seen_connection_names:
            raise EditingConfigValidationError(
                f"La conexión de origen '{source_connection.name}' está duplicada"
            )

        seen_connection_names.add(source_connection.name)


def _validate_tables(config: EditingConfigDto) -> None:
    available_connections = {
        source_connection.name for source_connection in config.source_connections
    }
    seen_logical_names: set[str] = set()
    destination_tables: dict[str, str] = {}

    for table in config.tables:
        if table.logical_name in seen_logical_names:
            raise EditingConfigValidationError(
                f"La tabla lógica '{table.logical_name}' está duplicada"
            )

        seen_logical_names.add(table.logical_name)
        _validate_table(table, available_connections, destination_tables)


def _validate_table(
    table: EditingTableDto,
    available_connections: set[str],
    destination_tables: dict[str, str],
) -> None:
    if table.source_adapter not in SUPPORTED_SOURCE_ADAPTERS:
        raise EditingConfigValidationError(
            f"La tabla '{table.logical_name}'.source.adapter solo admite "
            f"{', '.join(sorted(SUPPORTED_SOURCE_ADAPTERS))}"
        )

    if table.sync_mode not in SUPPORTED_SYNC_MODES:
        raise EditingConfigValidationError(
            f"La tabla '{table.logical_name}'.sync.mode solo admite "
            f"{', '.join(sorted(SUPPORTED_SYNC_MODES))}"
        )

    if table.source_connection not in available_connections:
        raise EditingConfigValidationError(
            f"La tabla '{table.logical_name}'.source.connection referencia "
            f"la conexión inexistente '{table.source_connection}'"
        )

    if not table.primary_key_fields:
        raise EditingConfigValidationError(
            f"La tabla '{table.logical_name}'.pk debe incluir al menos una columna"
        )

    if len(set(table.primary_key_fields)) != len(table.primary_key_fields):
        raise EditingConfigValidationError(
            f"La tabla '{table.logical_name}'.pk tiene columnas duplicadas"
        )

    if any(not field_name.strip() for field_name in table.primary_key_fields):
        raise EditingConfigValidationError(
            f"La tabla '{table.logical_name}'.pk no puede incluir valores vacíos"
        )

    conflicting_logical_name = destination_tables.get(table.destination_table)
    if conflicting_logical_name is not None:
        raise EditingConfigValidationError(
            f"La tabla de destino '{table.destination_table}' está duplicada para "
            f"'{conflicting_logical_name}' y '{table.logical_name}'"
        )

    destination_tables[table.destination_table] = table.logical_name
    _validate_destination(table)


def _validate_destination(
    table: EditingTableDto,
) -> None:
    if not table.destination_columns:
        raise EditingConfigValidationError(
            f"La tabla '{table.logical_name}'.destination.columns debe incluir al menos una columna"
        )

    destination_columns_by_name: dict[str, bool] = {}

    for column in table.destination_columns:
        if column.name in RESERVED_DESTINATION_COLUMNS:
            raise EditingConfigValidationError(
                f"La tabla '{table.logical_name}'.destination.columns no puede declarar "
                f"la columna técnica '{column.name}'"
            )

        if column.name in destination_columns_by_name:
            raise EditingConfigValidationError(
                f"La tabla '{table.logical_name}'.destination.columns tiene la columna "
                f"duplicada '{column.name}'"
            )

        destination_columns_by_name[column.name] = _resolve_nullable(
            column.nullable,
            table.destination_default_nullable,
        )

    for primary_key_field in table.primary_key_fields:
        column_nullable = destination_columns_by_name.get(primary_key_field)
        if column_nullable is None:
            raise EditingConfigValidationError(
                f"La tabla '{table.logical_name}'.destination.columns debe incluir "
                f"la columna de PK '{primary_key_field}'"
            )

        if column_nullable:
            raise EditingConfigValidationError(
                f"La tabla '{table.logical_name}'.destination.columns marca "
                f"la PK '{primary_key_field}' como nullable"
            )


def _resolve_nullable(nullable: bool | None, default_nullable: bool | None) -> bool:
    if nullable is not None:
        return nullable

    if default_nullable is not None:
        return default_nullable

    return False
