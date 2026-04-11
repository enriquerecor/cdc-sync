from dataclasses import dataclass

from clickhouse_client import ClickHouseCommandExecutor
from clickhouse_table_registry import ClickHouseTableRegistry


@dataclass(frozen=True)
class ClickHouseSchemaManager:
    database_executor: ClickHouseCommandExecutor
    table_executor: ClickHouseCommandExecutor
    table_registry: ClickHouseTableRegistry

    def bootstrap(self) -> None:
        self.database_executor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{self.table_registry.database}`"
        )

        for table in self.table_registry.tables.values():
            self.table_executor.execute(table.create_table_query)
