from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from cdc_sync_api.application.ports.database_health_checker import (
    DependencyUnavailableError,
)
from cdc_sync_api.shared.settings import Settings, get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    return _build_engine(settings)


def _build_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        echo=settings.database_echo,
    )


class SqlAlchemyDatabaseHealthChecker:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def ensure_available(self) -> None:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise DependencyUnavailableError(
                "La base de datos del control plane no está disponible"
            ) from exc
