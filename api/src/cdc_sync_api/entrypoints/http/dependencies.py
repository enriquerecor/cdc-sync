from cdc_sync_api.application.use_cases.delete_editing_config import (
    DeleteEditingConfigUseCase,
)
from cdc_sync_api.application.use_cases.get_editing_config import (
    GetEditingConfigUseCase,
)
from cdc_sync_api.application.use_cases.check_health import CheckHealthUseCase
from cdc_sync_api.application.ports.editing_config_repository import (
    EditingConfigRepository,
)
from cdc_sync_api.application.use_cases.save_editing_config import (
    SaveEditingConfigUseCase,
)
from cdc_sync_api.infrastructure.persistence.config_editing_repository import (
    SqlAlchemyEditingConfigRepository,
)
from cdc_sync_api.infrastructure.persistence.sqlalchemy import (
    SqlAlchemyDatabaseHealthChecker,
    get_engine,
)


def get_health_use_case() -> CheckHealthUseCase:
    return CheckHealthUseCase(
        database_health_checker=SqlAlchemyDatabaseHealthChecker(get_engine()),
    )


def get_editing_config_use_case() -> GetEditingConfigUseCase:
    return GetEditingConfigUseCase(get_editing_config_repository())


def get_save_editing_config_use_case() -> SaveEditingConfigUseCase:
    return SaveEditingConfigUseCase(get_editing_config_repository())


def get_delete_editing_config_use_case() -> DeleteEditingConfigUseCase:
    return DeleteEditingConfigUseCase(get_editing_config_repository())


def get_editing_config_repository() -> EditingConfigRepository:
    return SqlAlchemyEditingConfigRepository(get_engine())
