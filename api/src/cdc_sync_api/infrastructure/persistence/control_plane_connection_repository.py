from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from cdc_sync_api.domain.control_plane import (
    Destination,
    SecretReference,
    SourceConnection,
)
from cdc_sync_api.infrastructure.persistence.control_plane_repository_common import (
    raise_conflict,
)
from cdc_sync_api.infrastructure.persistence.control_plane_repository_mappers import (
    build_destination,
    build_source_connection,
    destination_values,
    source_connection_values,
)
from cdc_sync_api.infrastructure.persistence.control_plane_tables import (
    destinations,
    source_connections,
)


class ConnectionPersistenceMixin:
    def list_source_connections(self) -> tuple[SourceConnection, ...]:
        with self._engine.begin() as connection:
            rows = connection.execute(
                select(source_connections).order_by(source_connections.c.name)
            ).mappings().all()

        return tuple(build_source_connection(row) for row in rows)

    def save_source_connection(self, source_connection: SourceConnection) -> None:
        try:
            with self._engine.begin() as connection:
                connection.execute(
                    source_connections.insert().values(
                        source_connection_values(source_connection)
                    )
                )
        except IntegrityError as exc:
            raise_conflict("La conexión de origen no se puede persistir", exc)

    def save_source_connection_with_credentials(
        self,
        source_connection: SourceConnection,
        credentials: SecretReference,
    ) -> None:
        try:
            with self._engine.begin() as connection:
                self._insert_secret_reference(connection, credentials)
                connection.execute(
                    source_connections.insert().values(
                        source_connection_values(source_connection)
                    )
                )
        except IntegrityError as exc:
            raise_conflict("La conexión de origen no se puede persistir", exc)

    def get_source_connection(
        self,
        source_connection_id: UUID,
    ) -> SourceConnection | None:
        with self._engine.begin() as connection:
            row = connection.execute(
                select(source_connections).where(
                    source_connections.c.id == source_connection_id
                )
            ).mappings().first()

        if row is None:
            return None

        return build_source_connection(row)

    def update_source_connection(
        self,
        source_connection: SourceConnection,
        credentials: SecretReference | None,
    ) -> bool:
        try:
            with self._engine.begin() as connection:
                result = connection.execute(
                    source_connections.update()
                    .where(source_connections.c.id == source_connection.id)
                    .values(
                        name=source_connection.name,
                        source_type=source_connection.source_type.value,
                        host=source_connection.host,
                        port=source_connection.port,
                        database_name=source_connection.database_name,
                        updated_at=func.now(),
                    )
                )
                self._update_secret_reference(connection, credentials)
        except IntegrityError as exc:
            raise_conflict("La conexión de origen no se puede actualizar", exc)

        return result.rowcount > 0

    def delete_source_connection(self, source_connection_id: UUID) -> bool:
        try:
            with self._engine.begin() as connection:
                row = connection.execute(
                    select(source_connections.c.credentials_secret_id).where(
                        source_connections.c.id == source_connection_id
                    )
                ).mappings().first()
                if row is None:
                    return False

                result = connection.execute(
                    source_connections.delete().where(
                        source_connections.c.id == source_connection_id
                    )
                )
                self._delete_secret_if_unreferenced(
                    connection,
                    row["credentials_secret_id"],
                )
        except IntegrityError as exc:
            raise_conflict("No se puede eliminar una conexión asignada a configs", exc)

        return result.rowcount > 0

    def list_destinations(self) -> tuple[Destination, ...]:
        with self._engine.begin() as connection:
            rows = connection.execute(
                select(destinations).order_by(destinations.c.name)
            ).mappings().all()

        return tuple(build_destination(row) for row in rows)

    def save_destination(self, destination: Destination) -> None:
        try:
            with self._engine.begin() as connection:
                connection.execute(
                    destinations.insert().values(destination_values(destination))
                )
        except IntegrityError as exc:
            raise_conflict("El destino no se puede persistir", exc)

    def save_destination_with_credentials(
        self,
        destination: Destination,
        credentials: SecretReference,
    ) -> None:
        try:
            with self._engine.begin() as connection:
                self._insert_secret_reference(connection, credentials)
                connection.execute(
                    destinations.insert().values(destination_values(destination))
                )
        except IntegrityError as exc:
            raise_conflict("El destino no se puede persistir", exc)

    def get_destination(self, destination_id: UUID) -> Destination | None:
        with self._engine.begin() as connection:
            row = connection.execute(
                select(destinations).where(destinations.c.id == destination_id)
            ).mappings().first()

        if row is None:
            return None

        return build_destination(row)

    def update_destination(
        self,
        destination: Destination,
        credentials: SecretReference | None,
    ) -> bool:
        try:
            with self._engine.begin() as connection:
                result = connection.execute(
                    destinations.update()
                    .where(destinations.c.id == destination.id)
                    .values(
                        name=destination.name,
                        destination_type=destination.destination_type.value,
                        host=destination.host,
                        port=destination.port,
                        secure=destination.secure,
                        database_name=destination.database_name,
                        updated_at=func.now(),
                    )
                )
                self._update_secret_reference(connection, credentials)
        except IntegrityError as exc:
            raise_conflict("El destino no se puede actualizar", exc)

        return result.rowcount > 0

    def delete_destination(self, destination_id: UUID) -> bool:
        try:
            with self._engine.begin() as connection:
                row = connection.execute(
                    select(destinations.c.credentials_secret_id).where(
                        destinations.c.id == destination_id
                    )
                ).mappings().first()
                if row is None:
                    return False

                result = connection.execute(
                    destinations.delete().where(destinations.c.id == destination_id)
                )
                self._delete_secret_if_unreferenced(
                    connection,
                    row["credentials_secret_id"],
                )
        except IntegrityError as exc:
            raise_conflict("No se puede eliminar un destino asignado a configs", exc)

        return result.rowcount > 0
