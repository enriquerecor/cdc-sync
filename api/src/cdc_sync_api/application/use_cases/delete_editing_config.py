from datetime import datetime

from cdc_sync_api.application.errors import (
    EditingConfigConflictError,
    EditingConfigNotFoundError,
)
from cdc_sync_api.application.ports.editing_config_repository import (
    EditingConfigRepository,
)


class DeleteEditingConfigUseCase:
    def __init__(self, repository: EditingConfigRepository) -> None:
        self._repository = repository

    def execute(self, expected_updated_at: datetime | None) -> None:
        current_config = self._repository.get()
        if current_config is None:
            raise EditingConfigNotFoundError("No existe configuración en edición")

        _validate_concurrency(current_config.updated_at, expected_updated_at)
        deleted = self._repository.delete(expected_updated_at=current_config.updated_at)
        if deleted:
            return

        raise EditingConfigNotFoundError("No existe configuración en edición")


def _validate_concurrency(
    current_updated_at: datetime | None,
    expected_updated_at: datetime | None,
) -> None:
    if current_updated_at is None:
        raise EditingConfigConflictError(
            "La configuración en edición no tiene updated_at persistido"
        )

    if expected_updated_at is None:
        raise EditingConfigConflictError(
            "Debe indicar expected_updated_at para borrar la configuración en edición"
        )

    if current_updated_at == expected_updated_at:
        return

    raise EditingConfigConflictError(
        "La configuración en edición fue modificada por otra operación"
    )
