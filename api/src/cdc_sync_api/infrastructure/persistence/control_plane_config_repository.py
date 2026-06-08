from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from cdc_sync_api.domain.control_plane import (
    ConfiguredTable,
    DestinationColumn,
    SyncConfig,
)
from cdc_sync_api.infrastructure.persistence.control_plane_repository_common import (
    raise_conflict,
)
from cdc_sync_api.infrastructure.persistence.control_plane_repository_mappers import (
    config_values,
)
from cdc_sync_api.infrastructure.persistence.control_plane_tables import (
    config_table_destination_columns,
    config_table_primary_keys,
    config_tables,
    configs,
)


class ConfigPersistenceMixin:
    def list_configs(self) -> tuple[SyncConfig, ...]:
        with self._engine.begin() as connection:
            rows = connection.execute(
                select(configs).order_by(configs.c.name)
            ).mappings().all()

            return tuple(self._build_sync_config(connection, row) for row in rows)

    def save_config(self, config: SyncConfig) -> None:
        try:
            with self._engine.begin() as connection:
                connection.execute(configs.insert().values(config_values(config)))
                self._save_config_tables(connection, config)
        except IntegrityError as exc:
            raise_conflict("La configuración no se puede persistir", exc)

    def get_config(self, config_id: UUID) -> SyncConfig | None:
        with self._engine.begin() as connection:
            config_row = connection.execute(
                select(configs).where(configs.c.id == config_id)
            ).mappings().first()

            if config_row is None:
                return None

            return self._build_sync_config(connection, config_row)

    def update_config(self, config: SyncConfig) -> bool:
        try:
            with self._engine.begin() as connection:
                result = connection.execute(
                    configs.update()
                    .where(configs.c.id == config.id)
                    .values(
                        name=config.name,
                        source_connection_id=config.source_connection_id,
                        destination_id=config.destination_id,
                        sync_mode=config.sync_mode.value,
                        enabled=config.enabled,
                        updated_at=func.now(),
                    )
                )
                if result.rowcount == 0:
                    return False

                connection.execute(
                    config_tables.delete().where(
                        config_tables.c.config_id == config.id,
                    )
                )
                self._save_config_tables(connection, config)
        except IntegrityError as exc:
            raise_conflict("La configuración no se puede actualizar", exc)

        return True

    def delete_config(self, config_id: UUID) -> bool:
        try:
            with self._engine.begin() as connection:
                result = connection.execute(
                    configs.delete().where(configs.c.id == config_id)
                )
        except IntegrityError as exc:
            raise_conflict("No se puede eliminar una configuración asignada", exc)

        return result.rowcount > 0

    def _save_config_tables(self, connection, config: SyncConfig) -> None:
        for table_position, table in enumerate(config.tables):
            connection.execute(
                config_tables.insert().values(
                    id=table.id,
                    config_id=config.id,
                    logical_name=table.logical_name,
                    source_schema=table.source_schema,
                    source_table=table.source_table,
                    cdc_topic=table.cdc_topic,
                    destination_table=table.destination_table,
                    enabled=table.enabled,
                    position=table_position,
                )
            )
            self._save_primary_keys(connection, table)
            self._save_destination_columns(connection, table)

    def _save_primary_keys(self, connection, table: ConfiguredTable) -> None:
        connection.execute(
            config_table_primary_keys.insert(),
            [
                {
                    "config_table_id": table.id,
                    "column_name": column_name,
                    "position": position,
                }
                for position, column_name in enumerate(table.primary_key_fields)
            ],
        )

    def _save_destination_columns(self, connection, table: ConfiguredTable) -> None:
        connection.execute(
            config_table_destination_columns.insert(),
            [
                {
                    "id": uuid4(),
                    "config_table_id": table.id,
                    "name": column.name,
                    "destination_type": column.destination_type,
                    "nullable": column.nullable,
                    "position": position,
                }
                for position, column in enumerate(table.destination_columns)
            ],
        )

    def _build_sync_config(self, connection, config_row) -> SyncConfig:
        table_rows = connection.execute(
            select(config_tables)
            .where(config_tables.c.config_id == config_row["id"])
            .order_by(config_tables.c.position)
        ).mappings().all()

        tables = tuple(
            self._build_configured_table(connection, table_row)
            for table_row in table_rows
        )

        return SyncConfig(
            id=config_row["id"],
            name=config_row["name"],
            source_connection_id=config_row["source_connection_id"],
            destination_id=config_row["destination_id"],
            sync_mode=config_row["sync_mode"],
            enabled=config_row["enabled"],
            tables=tables,
        )

    def _build_configured_table(self, connection, table_row) -> ConfiguredTable:
        primary_key_rows = connection.execute(
            select(config_table_primary_keys)
            .where(config_table_primary_keys.c.config_table_id == table_row["id"])
            .order_by(config_table_primary_keys.c.position)
        ).mappings().all()
        column_rows = connection.execute(
            select(config_table_destination_columns)
            .where(config_table_destination_columns.c.config_table_id == table_row["id"])
            .order_by(config_table_destination_columns.c.position)
        ).mappings().all()

        return ConfiguredTable(
            id=table_row["id"],
            logical_name=table_row["logical_name"],
            source_schema=table_row["source_schema"],
            source_table=table_row["source_table"],
            cdc_topic=table_row["cdc_topic"],
            destination_table=table_row["destination_table"],
            enabled=table_row["enabled"],
            primary_key_fields=tuple(row["column_name"] for row in primary_key_rows),
            destination_columns=tuple(
                DestinationColumn(
                    name=row["name"],
                    destination_type=row["destination_type"],
                    nullable=row["nullable"],
                )
                for row in column_rows
            ),
        )
