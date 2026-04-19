from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from cdc_sync_api.shared.settings import get_settings

router = APIRouter(tags=["system"])


class ApiRootResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    docs_url: str


@router.get("/api/v1", response_model=ApiRootResponse)
def api_root() -> ApiRootResponse:
    settings = get_settings()
    return ApiRootResponse(
        name=settings.api_name,
        version=settings.api_version,
        docs_url="/docs",
    )
