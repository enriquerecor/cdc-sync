from __future__ import annotations

from typing import Protocol

from cdc_sync_api.application.dto.editing_config_dto import EditingConfigDto


class EditingConfigRepository(Protocol):
    def get(self) -> EditingConfigDto | None:
        """Obtiene la configuración en edición actual."""

    def save(
        self,
        *,
        config: EditingConfigDto,
        expected_version: int | None,
    ) -> EditingConfigDto:
        """Guarda la configuración en edición si la concurrencia es válida."""

    def delete(self, *, expected_version: int | None) -> bool:
        """Elimina la configuración en edición si la concurrencia es válida."""
