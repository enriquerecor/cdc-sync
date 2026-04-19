from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from cdc_sync_api.application.dto.health_check_dto import HealthCheckDto
from cdc_sync_api.application.ports.database_health_checker import (
    DependencyUnavailableError,
)
from cdc_sync_api.application.use_cases.check_health import CheckHealthUseCase
from cdc_sync_api.entrypoints.http.dependencies import get_health_use_case

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    checks: dict[str, str]

    @classmethod
    def from_dto(cls, dto: HealthCheckDto) -> "HealthResponse":
        return cls(
            status=dto.status,
            checks={"database": dto.database_status},
        )


@router.get("/health", response_model=HealthResponse)
def health(
    use_case: CheckHealthUseCase = Depends(get_health_use_case),
) -> HealthResponse:
    try:
        result = use_case.execute()
    except DependencyUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return HealthResponse.from_dto(result)
