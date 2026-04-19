from cdc_sync_api.application.dto.editing_config_dto import EditingConfigDto
from cdc_sync_api.application.errors import EditingConfigNotFoundError
from cdc_sync_api.application.ports.editing_config_repository import (
    EditingConfigRepository,
)


class GetEditingConfigUseCase:
    def __init__(self, repository: EditingConfigRepository) -> None:
        self._repository = repository

    def execute(self) -> EditingConfigDto:
        config = self._repository.get()
        if config is None:
            raise EditingConfigNotFoundError(
                "No existe configuración en edición"
            )

        return config
