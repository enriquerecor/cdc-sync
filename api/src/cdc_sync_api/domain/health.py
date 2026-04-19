from dataclasses import dataclass
from enum import StrEnum


class HealthStatus(StrEnum):
    OK = "ok"


@dataclass(frozen=True)
class ServiceHealth:
    status: HealthStatus
    database_status: HealthStatus
