from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from cdc_sync_api.application.errors import EditingConfigConflictError
from cdc_sync_api.infrastructure.persistence.config_editing_repository import (
    _raise_conflict_on_concurrent_initial_save,
)


def test_initial_save_conflict_maps_integrity_error_to_domain_conflict() -> None:
    database_error = IntegrityError(
        statement="INSERT INTO control_plane.config_editing ...",
        params={},
        orig=RuntimeError("duplicate key"),
    )

    try:
        _raise_conflict_on_concurrent_initial_save(
            current_row=None,
            expected_updated_at=None,
            error=database_error,
        )
    except EditingConfigConflictError as exc:
        assert str(exc) == "La configuración en edición fue modificada por otra operación"
        assert exc.__cause__ is database_error
    else:
        raise AssertionError("Se esperaba un conflicto de concurrencia")
