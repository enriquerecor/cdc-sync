from dataclasses import dataclass
from typing import Protocol, Sequence

from clickhouse_driver import Client

from config import ClickHouseConfig


class ClickHouseCommandExecutor(Protocol):
    def execute(self, query: str) -> None:
        """Execute a DDL or control statement against ClickHouse."""


class ClickHouseRowWriter(Protocol):
    def insert_rows(self, query: str, rows: Sequence[dict[str, object]]) -> None:
        """Insert normalized rows into ClickHouse."""


@dataclass
class ClickHouseClient(ClickHouseCommandExecutor, ClickHouseRowWriter):
    config: ClickHouseConfig
    database: str | None = None
    _client: Client | None = None

    def execute(self, query: str) -> None:
        self._get_client().execute(query)

    def insert_rows(self, query: str, rows: Sequence[dict[str, object]]) -> None:
        self._get_client().execute(query, list(rows))

    def _get_client(self) -> Client:
        if self._client is None:
            client_kwargs = {
                "host": self.config.host,
                "port": self.config.port,
                "secure": self.config.secure,
                "user": self.config.user,
                "password": self.config.password,
            }
            if self.database is not None:
                client_kwargs["database"] = self.database

            self._client = Client(**client_kwargs)

        return self._client
