from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    api_name: str = Field(default="cdc-sync control plane", validation_alias="API_NAME")
    api_version: str = Field(default="0.1.0", validation_alias="API_VERSION")
    api_port: int = Field(default=8000, gt=0, validation_alias="API_PORT")
    kafka_connect_base_url: str = Field(
        default="http://localhost:8083",
        validation_alias="API_KAFKA_CONNECT_BASE_URL",
    )
    worker_kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        min_length=1,
        validation_alias="API_WORKER_KAFKA_BOOTSTRAP_SERVERS",
    )
    worker_kafka_client_id_prefix: str = Field(
        default="cdc-sync-worker",
        min_length=1,
        validation_alias="API_WORKER_KAFKA_CLIENT_ID_PREFIX",
    )
    worker_kafka_auto_offset_reset: Literal["earliest", "latest"] = Field(
        default="earliest",
        validation_alias="API_WORKER_KAFKA_AUTO_OFFSET_RESET",
    )
    worker_kafka_poll_timeout_ms: int = Field(
        default=1000,
        gt=0,
        validation_alias="API_WORKER_KAFKA_POLL_TIMEOUT_MS",
    )
    cors_allowed_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="API_CORS_ALLOWED_ORIGINS",
    )
    database_host: str = Field(default="localhost", validation_alias="API_DATABASE_HOST")
    database_port: int = Field(
        default=5433,
        gt=0,
        validation_alias="API_DATABASE_PORT",
    )
    database_name: str = Field(
        default="cdc_sync_control_plane",
        validation_alias="API_DATABASE_NAME",
    )
    database_user: str = Field(
        default="cdc_sync_control_plane",
        validation_alias="API_DATABASE_USER",
    )
    database_password: str = Field(
        default="cdc_sync_control_plane",
        validation_alias="API_DATABASE_PASSWORD",
    )
    database_echo: bool = Field(default=False, validation_alias="API_DATABASE_ECHO")

    @field_validator(
        "worker_kafka_bootstrap_servers",
        "worker_kafka_client_id_prefix",
    )
    @classmethod
    def _normalize_required_text(cls, value: str) -> str:
        normalized_value = value.strip()
        if normalized_value:
            return normalized_value

        raise ValueError("El valor no puede estar vacío")

    @field_validator("cors_allowed_origins_raw")
    @classmethod
    def _normalize_cors_allowed_origins(cls, value: str) -> str:
        allowed_origins = cls._parse_cors_allowed_origins(value)
        return ",".join(allowed_origins)

    @property
    def database_url(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.database_user}:{self.database_password}@"
            f"{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def cors_allowed_origins(self) -> list[str]:
        return self._parse_cors_allowed_origins(self.cors_allowed_origins_raw)

    @staticmethod
    def _parse_cors_allowed_origins(value: str) -> list[str]:
        allowed_origins = [
            origin.strip()
            for origin in value.split(",")
            if origin.strip()
        ]

        if allowed_origins:
            return allowed_origins

        raise ValueError("Debe configurarse al menos un origen CORS permitido")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
