from typing import Protocol
from uuid import UUID

from cdc_sync_api.application.dto.control_plane_assignment_dto import (
    WorkerConfigAssignmentDto,
)
from cdc_sync_api.domain.control_plane import (
    Destination,
    SecretReference,
    SourceConnection,
    SyncConfig,
    Worker,
    WorkerConfigAssignment,
)


class ControlPlaneRepository(Protocol):
    def save_secret_reference(self, secret_reference: SecretReference) -> None:
        """Persiste una referencia de secreto validada."""

    def save_worker(self, worker: Worker) -> None:
        """Persiste un worker administrativo validado."""

    def save_source_connection(self, source_connection: SourceConnection) -> None:
        """Persiste una conexión de origen validada."""

    def save_destination(self, destination: Destination) -> None:
        """Persiste un destino analítico validado."""

    def save_config(self, config: SyncConfig) -> None:
        """Persiste una configuración completa validada."""

    def assign_config_to_worker(self, assignment: WorkerConfigAssignment) -> None:
        """Define la configuración efectiva de un worker."""

    def get_worker_by_identifier(self, worker_id: str) -> Worker | None:
        """Obtiene un worker por el identificador usado como WORKER_ID."""

    def get_config(self, config_id: UUID) -> SyncConfig | None:
        """Obtiene una configuración administrativa por id."""

    def get_assignment_for_worker(
        self,
        worker_id: str,
    ) -> WorkerConfigAssignmentDto | None:
        """Obtiene la asignación efectiva del worker indicado."""
