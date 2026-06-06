from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from cdc_sync_api.domain.control_plane import SecretReference
from cdc_sync_api.infrastructure.persistence.control_plane_repository_common import (
    raise_conflict,
)
from cdc_sync_api.infrastructure.persistence.control_plane_tables import (
    destinations,
    secret_references,
    source_connections,
)


class SecretPersistenceMixin:
    def save_secret_reference(self, secret_reference: SecretReference) -> None:
        try:
            with self._engine.begin() as connection:
                self._insert_secret_reference(connection, secret_reference)
        except IntegrityError as exc:
            raise_conflict("El secreto indicado ya existe o no es válido", exc)

    def get_secret_reference(self, secret_id: UUID) -> SecretReference | None:
        with self._engine.begin() as connection:
            row = connection.execute(
                select(secret_references).where(secret_references.c.id == secret_id)
            ).mappings().first()

        if row is None:
            return None

        return SecretReference(
            id=row["id"],
            name=row["name"],
            provider=row["provider"],
            inline_payload=row["inline_payload"],
            external_reference=row["external_reference"],
        )

    def _insert_secret_reference(
        self,
        connection,
        secret_reference: SecretReference,
    ) -> None:
        connection.execute(
            secret_references.insert().values(
                id=secret_reference.id,
                name=secret_reference.name,
                provider=secret_reference.provider.value,
                inline_payload=dict(secret_reference.inline_payload or {}),
                external_reference=secret_reference.external_reference,
            )
        )

    def _update_secret_reference(
        self,
        connection,
        secret_reference: SecretReference | None,
    ) -> None:
        if secret_reference is None:
            return

        connection.execute(
            secret_references.update()
            .where(secret_references.c.id == secret_reference.id)
            .values(
                inline_payload=dict(secret_reference.inline_payload or {}),
                updated_at=func.now(),
            )
        )

    def _delete_secret_if_unreferenced(self, connection, secret_id: UUID) -> None:
        source_row = connection.execute(
            select(source_connections.c.id).where(
                source_connections.c.credentials_secret_id == secret_id
            )
        ).first()
        if source_row is not None:
            return

        destination_row = connection.execute(
            select(destinations.c.id).where(
                destinations.c.credentials_secret_id == secret_id
            )
        ).first()
        if destination_row is not None:
            return

        connection.execute(
            secret_references.delete().where(secret_references.c.id == secret_id)
        )
