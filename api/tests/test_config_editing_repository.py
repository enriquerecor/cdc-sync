from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError

from cdc_sync_api.application.errors import EditingConfigConflictError
from cdc_sync_api.infrastructure.persistence.config_editing_repository import (
    CONSISTENT_READ_ISOLATION_LEVEL,
    SqlAlchemyEditingConfigRepository,
    _load_next_version,
    _raise_conflict_on_concurrent_initial_save,
)
from cdc_sync_api.infrastructure.persistence.config_editing_tables import (
    config_editing_table,
    config_editing_version_seq,
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
            expected_version=None,
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


def test_load_next_version_reads_sequence_value() -> None:
    connection = FakeScalarConnection(next_scalar=8)

    result = _load_next_version(connection)

    assert result == 8
    assert connection.scalar_calls == 1


def test_version_sequence_belongs_to_control_plane_schema() -> None:
    assert config_editing_version_seq.schema == "control_plane"
    assert config_editing_version_seq.name == "config_editing_version_seq"


def test_table_source_connection_fk_is_cascade_compatible() -> None:
    foreign_key_constraint = next(
        constraint
        for constraint in config_editing_table.foreign_key_constraints
        if len(constraint.column_keys) == 2
    )

    assert foreign_key_constraint.ondelete == "CASCADE"


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


class FakeScalarConnection:
    def __init__(self, *, next_scalar: int) -> None:
        self._next_scalar = next_scalar
        self.scalar_calls = 0

    def execute(self, _statement: object) -> "FakeScalarResult":
        self.scalar_calls += 1
        return FakeScalarResult(self._next_scalar)


class FakeScalarResult:
    def __init__(self, value: int) -> None:
        self._value = value

    def scalar_one(self) -> int:
        return self._value
