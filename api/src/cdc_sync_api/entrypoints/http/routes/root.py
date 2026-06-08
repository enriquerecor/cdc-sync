from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from cdc_sync_api.shared.settings import get_settings

router = APIRouter(tags=["system"])


class ApiRootResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "examples": [
                {
                    "name": "cdc-sync control plane",
                    "version": "0.1.0",
                    "docs_url": "/docs",
                    "redoc_url": "/redoc",
                    "openapi_url": "/openapi.json",
                }
            ]
        },
    )

    name: str
    version: str
    docs_url: str
    redoc_url: str
    openapi_url: str


@router.get(
    "/api/v1",
    response_model=ApiRootResponse,
    summary="Descubrir API",
    description="Devuelve metadatos básicos y URLs de documentación del control plane.",
    response_description="Metadatos públicos de la API.",
)
def api_root() -> ApiRootResponse:
    settings = get_settings()
    return ApiRootResponse(
        name=settings.api_name,
        version=settings.api_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
