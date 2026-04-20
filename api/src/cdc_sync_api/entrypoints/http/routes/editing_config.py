from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from cdc_sync_api.application.errors import (
    EditingConfigConflictError,
    EditingConfigNotFoundError,
)
from cdc_sync_api.application.services.editing_config_validator import (
    EditingConfigValidationError,
)
from cdc_sync_api.application.use_cases.delete_editing_config import (
    DeleteEditingConfigUseCase,
)
from cdc_sync_api.application.use_cases.get_editing_config import (
    GetEditingConfigUseCase,
)
from cdc_sync_api.application.use_cases.save_editing_config import (
    SaveEditingConfigUseCase,
)
from cdc_sync_api.entrypoints.http.dependencies import (
    get_delete_editing_config_use_case,
    get_editing_config_use_case,
    get_save_editing_config_use_case,
)
from cdc_sync_api.entrypoints.http.routes.editing_config_models import (
    EditingConfigResponse,
    PutEditingConfigRequest,
)

router = APIRouter(prefix="/api/v1/editing-config", tags=["editing-config"])


@router.get("", response_model=EditingConfigResponse)
def get_editing_config(
    use_case: GetEditingConfigUseCase = Depends(get_editing_config_use_case),
) -> EditingConfigResponse:
    try:
        result = use_case.execute()
    except EditingConfigNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return EditingConfigResponse.from_dto(result)


@router.put("", response_model=EditingConfigResponse)
def put_editing_config(
    request: PutEditingConfigRequest,
    use_case: SaveEditingConfigUseCase = Depends(get_save_editing_config_use_case),
) -> EditingConfigResponse:
    try:
        result = use_case.execute(request.to_dto())
    except EditingConfigValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except EditingConfigConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return EditingConfigResponse.from_dto(result)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_editing_config(
    expected_version: int | None = Query(default=None, gt=0),
    use_case: DeleteEditingConfigUseCase = Depends(
        get_delete_editing_config_use_case
    ),
) -> Response:
    try:
        use_case.execute(expected_version)
    except EditingConfigConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except EditingConfigNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
