from cdc_sync_api.application.dto.editing_config_dto import (
    EditingConfigDto,
    SaveEditingConfigDto,
)
from cdc_sync_api.application.errors import EditingConfigConflictError
from cdc_sync_api.application.ports.editing_config_repository import (
    EditingConfigRepository,
)
from cdc_sync_api.application.services.editing_config_validator import (
    validate_editing_config,
)


class SaveEditingConfigUseCase:
    def __init__(self, repository: EditingConfigRepository) -> None:
        self._repository = repository

    def execute(self, request: SaveEditingConfigDto) -> EditingConfigDto:
        config = EditingConfigDto(
            version=None,
            updated_at=None,
            source_connections=request.source_connections,
            tables=request.tables,
        )
        validate_editing_config(config)
        current_config = self._repository.get()
        _validate_concurrency(current_config, request.expected_version)

        expected_version = None
        if current_config is not None:
            expected_version = current_config.version

        return self._repository.save(
            config=config,
            expected_version=expected_version,
        )


def _validate_concurrency(
    current_config: EditingConfigDto | None,
    expected_version: int | None,
) -> None:
    if current_config is None:
        if expected_version is None:
            return

        raise EditingConfigConflictError(
            "No existe configuración en edición para la version indicada"
        )

    if expected_version is None:
        raise EditingConfigConflictError(
            "Debe indicar expected_version para sobrescribir la configuración en edición"
        )

    if current_config.version == expected_version:
        return

    raise EditingConfigConflictError(
        "La configuración en edición fue modificada por otra operación"
    )
