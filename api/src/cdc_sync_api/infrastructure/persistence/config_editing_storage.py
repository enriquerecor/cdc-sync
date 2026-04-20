from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa

from cdc_sync_api.application.dto.editing_config_dto import (
    EditingConfigDto,
    EditingDestinationColumnDto,
    EditingSourceConnectionDto,
    EditingTableDto,
)
from cdc_sync_api.infrastructure.persistence.config_editing_tables import (
    CONFIG_EDITING_ID,
    config_editing_destination_column,
    config_editing_source_connection,
    config_editing_table,
    config_editing_table_pk,
)

def load_editing_config(
    connection: sa.Connection,
    *,
    version: int,
    updated_at: datetime,
) -> EditingConfigDto:
    return EditingConfigDto(
        version=version,
        updated_at=normalize_datetime(updated_at),
        source_connections=_load_source_connections(connection),
        tables=_load_tables(connection),
    )

def insert_editing_config(
    connection: sa.Connection,
    *,
    config: EditingConfigDto,
) -> None:
    _insert_source_connections(connection, config)
    _insert_tables(connection, config)

def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)

def _load_source_connections(
    connection: sa.Connection,
) -> tuple[EditingSourceConnectionDto, ...]:
    rows = connection.execute(
        sa.select(
            config_editing_source_connection.c.name,
            config_editing_source_connection.c.host,
            config_editing_source_connection.c.port,
            config_editing_source_connection.c.database_name,
            config_editing_source_connection.c.username,
            config_editing_source_connection.c.password,
        )
        .where(config_editing_source_connection.c.config_id == CONFIG_EDITING_ID)
        .order_by(config_editing_source_connection.c.position.asc())
    ).mappings()

    return tuple(
        EditingSourceConnectionDto(
            name=row["name"],
            host=row["host"],
            port=row["port"],
            database=row["database_name"],
            username=row["username"],
            password=row["password"],
        )
        for row in rows
    )

def _load_tables(connection: sa.Connection) -> tuple[EditingTableDto, ...]:
    table_rows = connection.execute(
        sa.select(config_editing_table)
        .where(config_editing_table.c.config_id == CONFIG_EDITING_ID)
        .order_by(config_editing_table.c.position.asc())
    ).mappings()

    return tuple(_load_table(connection, table_row) for table_row in table_rows)

def _load_table(
    connection: sa.Connection,
    table_row: sa.RowMapping,
) -> EditingTableDto:
    primary_key_rows = connection.execute(
        sa.select(config_editing_table_pk.c.field_name)
        .where(config_editing_table_pk.c.table_id == table_row["id"])
        .order_by(config_editing_table_pk.c.position.asc())
    ).mappings()
    destination_column_rows = connection.execute(
        sa.select(
            config_editing_destination_column.c.name,
            config_editing_destination_column.c.column_type,
            config_editing_destination_column.c.nullable,
        )
        .where(config_editing_destination_column.c.table_id == table_row["id"])
        .order_by(config_editing_destination_column.c.position.asc())
    ).mappings()

    return EditingTableDto(
        logical_name=table_row["logical_name"],
        enabled=table_row["enabled"],
        source_adapter=table_row["source_adapter"],
        source_connection=table_row["source_connection_name"],
        source_schema=table_row["source_schema"],
        source_table=table_row["source_table"],
        source_topic=table_row["source_topic"],
        primary_key_fields=tuple(row["field_name"] for row in primary_key_rows),
        sync_mode=table_row["sync_mode"],
        destination_table=table_row["destination_table"],
        destination_default_nullable=table_row["destination_default_nullable"],
        destination_columns=tuple(
            EditingDestinationColumnDto(
                name=row["name"],
                type=row["column_type"],
                nullable=row["nullable"],
            )
            for row in destination_column_rows
        ),
    )

def _insert_source_connections(
    connection: sa.Connection,
    config: EditingConfigDto,
) -> None:
    for position, source_connection in enumerate(config.source_connections):
        connection.execute(
            sa.insert(config_editing_source_connection).values(
                config_id=CONFIG_EDITING_ID,
                position=position,
                name=source_connection.name,
                host=source_connection.host,
                port=source_connection.port,
                database_name=source_connection.database,
                username=source_connection.username,
                password=source_connection.password,
            )
        )

def _insert_tables(connection: sa.Connection, config: EditingConfigDto) -> None:
    for position, table in enumerate(config.tables):
        table_id = connection.execute(
            sa.insert(config_editing_table)
            .values(
                config_id=CONFIG_EDITING_ID,
                position=position,
                logical_name=table.logical_name,
                enabled=table.enabled,
                source_adapter=table.source_adapter,
                source_connection_name=table.source_connection,
                source_schema=table.source_schema,
                source_table=table.source_table,
                source_topic=table.source_topic,
                sync_mode=table.sync_mode,
                destination_table=table.destination_table,
                destination_default_nullable=table.destination_default_nullable,
            )
            .returning(config_editing_table.c.id)
        ).scalar_one()
        _insert_primary_key_fields(connection, table_id=table_id, table=table)
        _insert_destination_columns(connection, table_id=table_id, table=table)


def _insert_primary_key_fields(
    connection: sa.Connection,
    *,
    table_id: int,
    table: EditingTableDto,
) -> None:
    for position, primary_key_field in enumerate(table.primary_key_fields):
        connection.execute(
            sa.insert(config_editing_table_pk).values(
                table_id=table_id,
                position=position,
                field_name=primary_key_field,
            )
        )


def _insert_destination_columns(
    connection: sa.Connection,
    *,
    table_id: int,
    table: EditingTableDto,
) -> None:
    for position, column in enumerate(table.destination_columns):
        connection.execute(
            sa.insert(config_editing_destination_column).values(
                table_id=table_id,
                position=position,
                name=column.name,
                column_type=column.type,
                nullable=column.nullable,
            )
        )
