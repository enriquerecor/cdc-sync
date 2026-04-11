from dataclasses import dataclass
from typing import Protocol

from clickhouse_driver import Client

from config import ClickHouseConfig


class ClickHouseCommandExecutor(Protocol):
    def execute(self, query: str) -> None:
        """Execute a DDL or control statement against ClickHouse."""


@dataclass
class ClickHouseClient(ClickHouseCommandExecutor):
    config: ClickHouseConfig
    database: str | None = None
    _client: Client | None = None

    def execute(self, query: str) -> None:
        self._get_client().execute(query)

    def _get_client(self) -> Client:
        if self._client is None:
            client_kwargs = {
                "host": self.config.host,
                "port": self.config.port,
                "user": self.config.user,
                "password": self.config.password,
            }
            if self.database is not None:
                client_kwargs["database"] = self.database

            self._client = Client(**client_kwargs)

        return self._client
