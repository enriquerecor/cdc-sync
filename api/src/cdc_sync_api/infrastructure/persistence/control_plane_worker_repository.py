from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from cdc_sync_api.domain.control_plane import Worker
from cdc_sync_api.infrastructure.persistence.control_plane_repository_common import (
    raise_conflict,
)
from cdc_sync_api.infrastructure.persistence.control_plane_repository_mappers import (
    build_worker,
    worker_values,
)
from cdc_sync_api.infrastructure.persistence.control_plane_tables import workers


class WorkerPersistenceMixin:
    def list_workers(self) -> tuple[Worker, ...]:
        with self._engine.begin() as connection:
            rows = connection.execute(
                select(workers).order_by(workers.c.name, workers.c.worker_id)
            ).mappings().all()

        return tuple(build_worker(row) for row in rows)

    def save_worker(self, worker: Worker) -> None:
        try:
            with self._engine.begin() as connection:
                connection.execute(workers.insert().values(worker_values(worker)))
        except IntegrityError as exc:
            raise_conflict("Ya existe un worker con ese identificador", exc)

    def get_worker(self, worker_id: UUID) -> Worker | None:
        with self._engine.begin() as connection:
            row = connection.execute(
                select(workers).where(workers.c.id == worker_id)
            ).mappings().first()

        if row is None:
            return None

        return build_worker(row)

    def get_worker_by_identifier(self, worker_id: str) -> Worker | None:
        with self._engine.begin() as connection:
            row = connection.execute(
                select(workers).where(workers.c.worker_id == worker_id)
            ).mappings().first()

        if row is None:
            return None

        return build_worker(row)

    def update_worker(self, worker: Worker) -> bool:
        try:
            with self._engine.begin() as connection:
                result = connection.execute(
                    workers.update()
                    .where(workers.c.id == worker.id)
                    .values(
                        worker_id=worker.worker_id,
                        name=worker.name,
                        description=worker.description,
                        enabled=worker.enabled,
                        updated_at=func.now(),
                    )
                )
        except IntegrityError as exc:
            raise_conflict("Ya existe un worker con ese identificador", exc)

        return result.rowcount > 0

    def delete_worker(self, worker_id: UUID) -> bool:
        try:
            with self._engine.begin() as connection:
                result = connection.execute(
                    workers.delete().where(workers.c.id == worker_id)
                )
        except IntegrityError as exc:
            raise_conflict("No se puede eliminar el worker indicado", exc)

        return result.rowcount > 0
