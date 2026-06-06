from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert

from cdc_sync_api.application.dto.control_plane_assignment_dto import (
    WorkerConfigAssignmentDto,
)
from cdc_sync_api.domain.control_plane import (
    ConfiguredTable,
    Destination,
    DestinationColumn,
    SecretReference,
    SourceConnection,
    SyncConfig,
    Worker,
    WorkerConfigAssignment,
)
from cdc_sync_api.infrastructure.persistence.control_plane_tables import (
    config_table_destination_columns,
    config_table_primary_keys,
    config_tables,
    configs,
    destinations,
    secret_references,
    source_connections,
    worker_config_assignments,
    workers,
)


class SqlAlchemyControlPlaneRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save_secret_reference(self, secret_reference: SecretReference) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                secret_references.insert().values(
                    id=secret_reference.id,
                    name=secret_reference.name,
                    provider=secret_reference.provider.value,
                    inline_payload=dict(secret_reference.inline_payload or {}),
                    external_reference=secret_reference.external_reference,
                )
            )

    def save_worker(self, worker: Worker) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                workers.insert().values(
                    id=worker.id,
                    worker_id=worker.worker_id,
                    name=worker.name,
                    description=worker.description,
                    enabled=worker.enabled,
                )
            )

    def save_source_connection(self, source_connection: SourceConnection) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                source_connections.insert().values(
                    id=source_connection.id,
                    name=source_connection.name,
                    source_type=source_connection.source_type.value,
                    host=source_connection.host,
                    port=source_connection.port,
                    database_name=source_connection.database_name,
                    credentials_secret_id=source_connection.credentials_secret_id,
                )
            )

    def save_destination(self, destination: Destination) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                destinations.insert().values(
                    id=destination.id,
                    name=destination.name,
                    destination_type=destination.destination_type.value,
                    host=destination.host,
                    port=destination.port,
                    secure=destination.secure,
                    database_name=destination.database_name,
                    credentials_secret_id=destination.credentials_secret_id,
                )
            )

    def save_config(self, config: SyncConfig) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                configs.insert().values(
                    id=config.id,
                    name=config.name,
                    source_connection_id=config.source_connection_id,
                    destination_id=config.destination_id,
                    sync_mode=config.sync_mode.value,
                    enabled=config.enabled,
                )
            )

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

    def assign_config_to_worker(self, assignment: WorkerConfigAssignment) -> None:
        statement = postgres_insert(worker_config_assignments).values(
            worker_id=assignment.worker_id,
            config_id=assignment.config_id,
            assigned_at=assignment.assigned_at,
        )
        upsert_statement = statement.on_conflict_do_update(
            index_elements=[worker_config_assignments.c.worker_id],
            set_={
                "config_id": statement.excluded.config_id,
                "assigned_at": statement.excluded.assigned_at,
            },
        )

        with self._engine.begin() as connection:
            connection.execute(upsert_statement)

    def get_worker_by_identifier(self, worker_id: str) -> Worker | None:
        statement = select(workers).where(workers.c.worker_id == worker_id)

        with self._engine.begin() as connection:
            row = connection.execute(statement).mappings().first()

        if row is None:
            return None

        return Worker(
            id=row["id"],
            worker_id=row["worker_id"],
            name=row["name"],
            description=row["description"],
            enabled=row["enabled"],
        )

    def get_config(self, config_id: UUID) -> SyncConfig | None:
        with self._engine.begin() as connection:
            config_row = connection.execute(
                select(configs).where(configs.c.id == config_id)
            ).mappings().first()

            if config_row is None:
                return None

            table_rows = connection.execute(
                select(config_tables)
                .where(config_tables.c.config_id == config_id)
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

    def get_assignment_for_worker(
        self,
        worker_id: str,
    ) -> WorkerConfigAssignmentDto | None:
        statement = (
            select(
                workers.c.id.label("worker_internal_id"),
                workers.c.worker_id.label("worker_identifier"),
                worker_config_assignments.c.config_id,
                worker_config_assignments.c.assigned_at,
            )
            .join(
                worker_config_assignments,
                worker_config_assignments.c.worker_id == workers.c.id,
            )
            .where(workers.c.worker_id == worker_id)
        )

        with self._engine.begin() as connection:
            row = connection.execute(statement).mappings().first()

        if row is None:
            return None

        return WorkerConfigAssignmentDto(
            worker_internal_id=row["worker_internal_id"],
            worker_id=row["worker_identifier"],
            config_id=row["config_id"],
            assigned_at=row["assigned_at"],
        )

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
