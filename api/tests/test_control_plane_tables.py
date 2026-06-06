from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from cdc_sync_api.infrastructure.persistence.control_plane_tables import (
    config_table_destination_columns,
    config_tables,
    control_plane_metadata,
    destinations,
    secret_references,
    source_connections,
    worker_config_assignments,
    workers,
)


def test_control_plane_metadata_defines_expected_tables() -> None:
    assert set(control_plane_metadata.tables) == {
        "control_plane.secret_references",
        "control_plane.workers",
        "control_plane.source_connections",
        "control_plane.destinations",
        "control_plane.configs",
        "control_plane.config_tables",
        "control_plane.config_table_primary_keys",
        "control_plane.config_table_destination_columns",
        "control_plane.worker_config_assignments",
    }


def test_workers_have_unique_runtime_identifier() -> None:
    assert "uq_workers_worker_id" in _constraint_names(workers, UniqueConstraint)


def test_assignment_has_worker_primary_key_for_one_effective_config() -> None:
    assert [column.name for column in worker_config_assignments.primary_key.columns] == [
        "worker_id"
    ]


def test_mvp_type_constraints_are_explicit() -> None:
    assert "ck_secret_references_provider" in _constraint_names(
        secret_references,
        CheckConstraint,
    )
    assert "ck_source_connections_source_type" in _constraint_names(
        source_connections,
        CheckConstraint,
    )
    assert "ck_destinations_destination_type" in _constraint_names(
        destinations,
        CheckConstraint,
    )


def test_config_tables_prevent_ambiguous_config_entries() -> None:
    unique_constraints = _constraint_names(config_tables, UniqueConstraint)

    assert "uq_config_tables_name" in unique_constraints
    assert "uq_config_tables_topic" in unique_constraints
    assert "uq_config_tables_destination_table" in unique_constraints


def test_destination_columns_reject_technical_columns_in_database() -> None:
    assert "ck_config_table_destination_columns_not_technical" in _constraint_names(
        config_table_destination_columns,
        CheckConstraint,
    )


def test_source_and_destination_credentials_reference_secret_store() -> None:
    assert _foreign_key_targets(source_connections) == {
        "control_plane.secret_references.id"
    }
    assert _foreign_key_targets(destinations) == {"control_plane.secret_references.id"}


def _constraint_names(table, constraint_type: type) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, constraint_type) and constraint.name is not None
    }


def _foreign_key_targets(table) -> set[str]:
    targets: set[str] = set()

    for constraint in table.constraints:
        if not isinstance(constraint, ForeignKeyConstraint):
            continue

        for element in constraint.elements:
            targets.add(f"{element.column.table.fullname}.{element.column.name}")

    return targets
