from functools import lru_cache

from pydantic import Field
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

    @property
    def database_url(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.database_user}:{self.database_password}@"
            f"{self.database_host}:{self.database_port}/{self.database_name}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
