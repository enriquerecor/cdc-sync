from cdc_sync_api.application.use_cases.check_health import CheckHealthUseCase
from cdc_sync_api.application.use_cases.manage_control_plane import (
    ManageControlPlaneUseCase,
)
from cdc_sync_api.infrastructure.persistence.control_plane_repository import (
    SqlAlchemyControlPlaneRepository,
)
from cdc_sync_api.infrastructure.persistence.sqlalchemy import (
    SqlAlchemyDatabaseHealthChecker,
    get_engine,
)


def get_health_use_case() -> CheckHealthUseCase:
    return CheckHealthUseCase(
        database_health_checker=SqlAlchemyDatabaseHealthChecker(get_engine()),
    )


def get_control_plane_admin_use_case() -> ManageControlPlaneUseCase:
    return ManageControlPlaneUseCase(
        repository=SqlAlchemyControlPlaneRepository(get_engine()),
    )
