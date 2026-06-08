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
    def list_workers(self) -> tuple[Worker, ...]:
        """Lista workers administrativos."""

    def save_secret_reference(self, secret_reference: SecretReference) -> None:
        """Persiste una referencia de secreto validada."""

    def get_secret_reference(self, secret_id: UUID) -> SecretReference | None:
        """Obtiene una referencia de secreto para uso interno del control plane."""

    def save_worker(self, worker: Worker) -> None:
        """Persiste un worker administrativo validado."""

    def get_worker(self, worker_id: UUID) -> Worker | None:
        """Obtiene un worker por id interno."""

    def save_source_connection(self, source_connection: SourceConnection) -> None:
        """Persiste una conexión de origen validada."""

    def save_source_connection_with_credentials(
        self,
        source_connection: SourceConnection,
        credentials: SecretReference,
    ) -> None:
        """Persiste una conexión de origen y sus credenciales en una operación."""

    def update_worker(self, worker: Worker) -> bool:
        """Actualiza un worker existente."""

    def delete_worker(self, worker_id: UUID) -> bool:
        """Elimina un worker existente."""

    def list_source_connections(self) -> tuple[SourceConnection, ...]:
        """Lista conexiones de origen."""

    def get_source_connection(
        self,
        source_connection_id: UUID,
    ) -> SourceConnection | None:
        """Obtiene una conexión de origen por id."""

    def update_source_connection(
        self,
        source_connection: SourceConnection,
        credentials: SecretReference | None,
    ) -> bool:
        """Actualiza una conexión de origen y, si procede, sus credenciales."""

    def delete_source_connection(self, source_connection_id: UUID) -> bool:
        """Elimina una conexión de origen existente."""

    def list_destinations(self) -> tuple[Destination, ...]:
        """Lista destinos analíticos."""

    def save_destination(self, destination: Destination) -> None:
        """Persiste un destino analítico validado."""

    def save_destination_with_credentials(
        self,
        destination: Destination,
        credentials: SecretReference,
    ) -> None:
        """Persiste un destino analítico y sus credenciales en una operación."""

    def get_destination(self, destination_id: UUID) -> Destination | None:
        """Obtiene un destino analítico por id."""

    def update_destination(
        self,
        destination: Destination,
        credentials: SecretReference | None,
    ) -> bool:
        """Actualiza un destino y, si procede, sus credenciales."""

    def delete_destination(self, destination_id: UUID) -> bool:
        """Elimina un destino analítico existente."""

    def list_configs(self) -> tuple[SyncConfig, ...]:
        """Lista configuraciones administrativas completas."""

    def save_config(self, config: SyncConfig) -> None:
        """Persiste una configuración completa validada."""

    def update_config(self, config: SyncConfig) -> bool:
        """Reemplaza una configuración administrativa completa."""

    def delete_config(self, config_id: UUID) -> bool:
        """Elimina una configuración administrativa existente."""

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
