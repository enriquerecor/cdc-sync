from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from cdc_sync_api.application.dto.editing_config_dto import EditingConfigDto
from cdc_sync_api.application.errors import EditingConfigConflictError
from cdc_sync_api.infrastructure.persistence.config_editing_storage import (
    insert_editing_config,
    load_editing_config,
)
from cdc_sync_api.infrastructure.persistence.config_editing_tables import (
    CONFIG_EDITING_ID,
    config_editing,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

import sqlalchemy as sa

CONSISTENT_READ_ISOLATION_LEVEL = "REPEATABLE READ"


class SqlAlchemyEditingConfigRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get(self) -> EditingConfigDto | None:
        with self._engine.connect() as raw_connection:
            connection = raw_connection.execution_options(
                # Garantiza lectura sobre la misma snapshot aunque se lea
                # en distintas queries, en la misma transacción.
                isolation_level=CONSISTENT_READ_ISOLATION_LEVEL
            )
            with connection.begin():
                config_row = connection.execute(
                    sa.select(
                        config_editing.c.version,
                        config_editing.c.updated_at,
                    ).where(
                        config_editing.c.id == CONFIG_EDITING_ID
                    )
                ).mappings().one_or_none()
                if config_row is None:
                    return None

                return load_editing_config(
                    connection,
                    version=config_row["version"],
                    updated_at=config_row["updated_at"],
                )

    def save(
        self,
        *,
        config: EditingConfigDto,
        expected_version: int | None,
    ) -> EditingConfigDto:
        with self._engine.begin() as connection:
            current_row = connection.execute(
                sa.select(
                    config_editing.c.version,
                    config_editing.c.updated_at,
                )
                .where(config_editing.c.id == CONFIG_EDITING_ID)
                .with_for_update()
            ).mappings().one_or_none()
            self._validate_expected_version(current_row, expected_version)
            persisted_version = _build_next_version(current_row)
            persisted_updated_at = datetime.now(UTC)

            if current_row is not None:
                connection.execute(
                    sa.delete(config_editing).where(
                        config_editing.c.id == CONFIG_EDITING_ID
                    )
                )

            try:
                connection.execute(
                    _build_insert_config_editing_statement(
                        persisted_version=persisted_version,
                        persisted_updated_at=persisted_updated_at,
                    )
                )
            except IntegrityError as exc:
                _raise_conflict_on_concurrent_initial_save(
                    current_row=current_row,
                    expected_version=expected_version,
                    error=exc,
                )
            insert_editing_config(connection, config=config)

        return replace(
            config,
            version=persisted_version,
            updated_at=persisted_updated_at,
        )

    def delete(self, *, expected_version: int | None) -> bool:
        with self._engine.begin() as connection:
            current_row = connection.execute(
                sa.select(config_editing.c.version)
                .where(config_editing.c.id == CONFIG_EDITING_ID)
                .with_for_update()
            ).mappings().one_or_none()
            self._validate_expected_version(current_row, expected_version)
            deleted_rows = connection.execute(
                sa.delete(config_editing).where(config_editing.c.id == CONFIG_EDITING_ID)
            )

        return deleted_rows.rowcount > 0

    def _validate_expected_version(
        self,
        current_row: sa.RowMapping | None,
        expected_version: int | None,
    ) -> None:
        if current_row is None:
            if expected_version is None:
                return

            raise EditingConfigConflictError(
                "No existe configuración en edición para la version indicada"
            )

        if expected_version is None:
            raise EditingConfigConflictError(
                "Debe indicar expected_version para sobrescribir la configuración en edición"
            )

        if current_row["version"] == expected_version:
            return

        raise EditingConfigConflictError(
            "La configuración en edición fue modificada por otra operación"
        )


def _build_insert_config_editing_statement(
    *,
    persisted_version: int,
    persisted_updated_at: datetime,
) -> sa.Insert:
    return sa.insert(config_editing).values(
        id=CONFIG_EDITING_ID,
        version=persisted_version,
        updated_at=persisted_updated_at,
    )


def _raise_conflict_on_concurrent_initial_save(
    *,
    current_row: sa.RowMapping | None,
    expected_version: int | None,
    error: IntegrityError,
) -> None:
    if current_row is None and expected_version is None:
        raise EditingConfigConflictError(
            "La configuración en edición fue modificada por otra operación"
        ) from error

    raise error


def _build_next_version(current_row: sa.RowMapping | None) -> int:
    if current_row is None:
        return 1

    return int(current_row["version"]) + 1
