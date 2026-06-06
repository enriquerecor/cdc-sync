from sqlalchemy.exc import IntegrityError

from cdc_sync_api.application.errors import ControlPlaneConflictError


def raise_conflict(message: str, exc: IntegrityError) -> None:
    raise ControlPlaneConflictError(message) from exc
