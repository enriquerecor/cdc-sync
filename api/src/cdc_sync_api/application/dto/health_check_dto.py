from dataclasses import dataclass

from cdc_sync_api.domain.health import HealthStatus


@dataclass(frozen=True)
class HealthCheckDto:
    status: HealthStatus
    database_status: HealthStatus
