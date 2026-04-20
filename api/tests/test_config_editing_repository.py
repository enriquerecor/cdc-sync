from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError

from cdc_sync_api.application.errors import EditingConfigConflictError
from cdc_sync_api.infrastructure.persistence.config_editing_repository import (
    CONSISTENT_READ_ISOLATION_LEVEL,
    SqlAlchemyEditingConfigRepository,
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


def test_get_uses_repeatable_read_transaction_for_consistent_snapshot() -> None:
    engine = FakeEngine()
    repository = SqlAlchemyEditingConfigRepository(engine)

    result = repository.get()

    assert result is None
    assert engine.connection.execution_options_calls == [
        {"isolation_level": CONSISTENT_READ_ISOLATION_LEVEL}
    ]
    assert engine.connection.begin_calls == 1
    assert engine.connection.execute_calls == 1


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    @contextmanager
    def connect(self) -> Iterator["FakeConnection"]:
        yield self.connection


class FakeConnection:
    def __init__(self) -> None:
        self.execution_options_calls: list[dict[str, str]] = []
        self.begin_calls = 0
        self.execute_calls = 0

    def execution_options(self, **kwargs: str) -> "FakeConnection":
        self.execution_options_calls.append(kwargs)
        return self

    @contextmanager
    def begin(self) -> Iterator[None]:
        self.begin_calls += 1
        yield None

    def execute(self, _statement: object) -> "FakeResult":
        self.execute_calls += 1
        return FakeResult()


class FakeResult:
    def mappings(self) -> "FakeResult":
        return self

    def one_or_none(self) -> None:
        return None
