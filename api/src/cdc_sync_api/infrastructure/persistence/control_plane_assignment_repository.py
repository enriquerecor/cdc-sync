from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert

from cdc_sync_api.application.dto.control_plane_assignment_dto import (
    WorkerConfigAssignmentDto,
)
from cdc_sync_api.domain.control_plane import WorkerConfigAssignment
from cdc_sync_api.infrastructure.persistence.control_plane_tables import (
    worker_config_assignments,
    workers,
)


class AssignmentPersistenceMixin:
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
