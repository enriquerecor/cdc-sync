from cdc_sync_api.application.dto.health_check_dto import HealthCheckDto
from cdc_sync_api.application.ports.database_health_checker import DatabaseHealthChecker
from cdc_sync_api.domain.health import HealthStatus, ServiceHealth


class CheckHealthUseCase:
    def __init__(self, database_health_checker: DatabaseHealthChecker) -> None:
        self._database_health_checker = database_health_checker

    def execute(self) -> HealthCheckDto:
        self._database_health_checker.ensure_available()
        service_health = ServiceHealth(
            status=HealthStatus.OK,
            database_status=HealthStatus.OK,
        )

        return HealthCheckDto(
            status=service_health.status,
            database_status=service_health.database_status,
        )
