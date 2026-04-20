from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from cdc_sync_api.application.dto.editing_config_dto import EditingConfigDto
from cdc_sync_api.application.errors import EditingConfigConflictError
from cdc_sync_api.infrastructure.persistence.config_editing_storage import (
    insert_editing_config,
    load_editing_config,
    normalize_datetime,
)
from cdc_sync_api.infrastructure.persistence.config_editing_tables import (
    CONFIG_EDITING_ID,
    config_editing,
)


class SqlAlchemyEditingConfigRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get(self) -> EditingConfigDto | None:
        with self._engine.connect() as connection:
            config_row = connection.execute(
                sa.select(config_editing.c.updated_at).where(
                    config_editing.c.id == CONFIG_EDITING_ID
                )
            ).mappings().one_or_none()
            if config_row is None:
                return None

            return load_editing_config(
                connection,
                updated_at=config_row["updated_at"],
            )

    def save(
        self,
        *,
        config: EditingConfigDto,
        expected_updated_at: datetime | None,
    ) -> EditingConfigDto:
        persisted_updated_at = datetime.now(UTC)

        with self._engine.begin() as connection:
            current_row = connection.execute(
                sa.select(config_editing.c.updated_at)
                .where(config_editing.c.id == CONFIG_EDITING_ID)
                .with_for_update()
            ).mappings().one_or_none()
            self._validate_expected_updated_at(current_row, expected_updated_at)

            if current_row is not None:
                connection.execute(
                    sa.delete(config_editing).where(
                        config_editing.c.id == CONFIG_EDITING_ID
                    )
                )

            try:
                connection.execute(
                    _build_insert_config_editing_statement(
                        persisted_updated_at=persisted_updated_at
                    )
                )
            except IntegrityError as exc:
                _raise_conflict_on_concurrent_initial_save(
                    current_row=current_row,
                    expected_updated_at=expected_updated_at,
                    error=exc,
                )
            insert_editing_config(connection, config=config)

        return replace(config, updated_at=persisted_updated_at)

    def delete(self, *, expected_updated_at: datetime | None) -> bool:
        with self._engine.begin() as connection:
            current_row = connection.execute(
                sa.select(config_editing.c.updated_at)
                .where(config_editing.c.id == CONFIG_EDITING_ID)
                .with_for_update()
            ).mappings().one_or_none()
            self._validate_expected_updated_at(current_row, expected_updated_at)
            deleted_rows = connection.execute(
                sa.delete(config_editing).where(config_editing.c.id == CONFIG_EDITING_ID)
            )

        return deleted_rows.rowcount > 0

    def _validate_expected_updated_at(
        self,
        current_row: sa.RowMapping | None,
        expected_updated_at: datetime | None,
    ) -> None:
        if current_row is None:
            if expected_updated_at is None:
                return

            raise EditingConfigConflictError(
                "No existe configuración en edición para el updated_at indicado"
            )

        if expected_updated_at is None:
            raise EditingConfigConflictError(
                "Debe indicar expected_updated_at para sobrescribir la configuración en edición"
            )

        current_updated_at = normalize_datetime(current_row["updated_at"])
        if normalize_datetime(expected_updated_at) == current_updated_at:
            return

        raise EditingConfigConflictError(
            "La configuración en edición fue modificada por otra operación"
        )


def _build_insert_config_editing_statement(
    *,
    persisted_updated_at: datetime,
) -> sa.Insert:
    return sa.insert(config_editing).values(
        id=CONFIG_EDITING_ID,
        updated_at=persisted_updated_at,
    )


def _raise_conflict_on_concurrent_initial_save(
    *,
    current_row: sa.RowMapping | None,
    expected_updated_at: datetime | None,
    error: IntegrityError,
) -> None:
    if current_row is None and expected_updated_at is None:
        raise EditingConfigConflictError(
            "La configuración en edición fue modificada por otra operación"
        ) from error

    raise error
