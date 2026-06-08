from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException, status

from cdc_sync_api.application.errors import (
    ControlPlaneConflictError,
    ControlPlaneNotFoundError,
    KafkaConnectRequestError,
)
from cdc_sync_api.domain.control_plane import ControlPlaneValidationError

OperationResult = TypeVar("OperationResult")


def execute_admin_operation(
    operation: Callable[[], OperationResult],
) -> OperationResult:
    try:
        return operation()
    except ControlPlaneNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ControlPlaneConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except KafkaConnectRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except (ControlPlaneValidationError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
