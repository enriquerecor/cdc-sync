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

    def execute(self, expected_version: int | None) -> None:
        current_config = self._repository.get()
        if current_config is None:
            raise EditingConfigNotFoundError("No existe configuración en edición")

        _validate_concurrency(current_config.version, expected_version)
        deleted = self._repository.delete(expected_version=current_config.version)
        if deleted:
            return

        raise EditingConfigNotFoundError("No existe configuración en edición")


def _validate_concurrency(
    current_version: int | None,
    expected_version: int | None,
) -> None:
    if current_version is None:
        raise EditingConfigConflictError(
            "La configuración en edición no tiene version persistida"
        )

    if expected_version is None:
        raise EditingConfigConflictError(
            "Debe indicar expected_version para borrar la configuración en edición"
        )

    if current_version == expected_version:
        return

    raise EditingConfigConflictError(
        "La configuración en edición fue modificada por otra operación"
    )
