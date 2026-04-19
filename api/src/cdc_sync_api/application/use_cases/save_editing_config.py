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
            updated_at=None,
            source_connections=request.source_connections,
            tables=request.tables,
        )
        validate_editing_config(config)
        current_config = self._repository.get()
        _validate_concurrency(current_config, request.expected_updated_at)

        expected_updated_at = None
        if current_config is not None:
            expected_updated_at = current_config.updated_at

        return self._repository.save(
            config=config,
            expected_updated_at=expected_updated_at,
        )


def _validate_concurrency(
    current_config: EditingConfigDto | None,
    expected_updated_at,
) -> None:
    if current_config is None:
        if expected_updated_at is None:
            return

        raise EditingConfigConflictError(
            "No existe configuración en edición para el updated_at indicado"
        )

    if expected_updated_at is None:
        raise EditingConfigConflictError(
            "Debe indicar expected_updated_at para sobrescribir la configuración en edición"
        )

    if current_config.updated_at == expected_updated_at:
        return

    raise EditingConfigConflictError(
        "La configuración en edición fue modificada por otra operación"
    )
