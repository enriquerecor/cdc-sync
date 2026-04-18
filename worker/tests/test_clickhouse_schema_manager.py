from dataclasses import dataclass

from clickhouse_schema_manager import ClickHouseSchemaManager
from clickhouse_table_registry import build_clickhouse_table_registry
from config import ClickHouseConfig

from .helpers import build_table_config


@dataclass
class FakeClickHouseExecutor:
    queries: list[str]

    def execute(self, query: str) -> None:
        self.queries.append(query)


def test_bootstrap_creates_database_and_tables() -> None:
    table_registry = build_clickhouse_table_registry(
        ClickHouseConfig(
            host="clickhouse",
            port=9000,
            secure=False,
            database="cdc_sync_analytics",
            user="cdc_sync",
            password="cdc_sync",
        ),
        tables={
            "customers": build_table_config(
                table="customers",
                topic="cdc_sync.public.customers",
                primary_key_fields=("id",),
                destination_columns=(
                    ("id", "UInt64", False),
                    ("email", "String", True),
                ),
            ),
            "orders": build_table_config(
                table="orders",
                topic="cdc_sync.public.orders",
                primary_key_fields=("id",),
                destination_columns=(
                    ("id", "UInt64", False),
                    ("status", "String", True),
                ),
            ),
        },
    )
    database_executor = FakeClickHouseExecutor(queries=[])
    table_executor = FakeClickHouseExecutor(queries=[])

    ClickHouseSchemaManager(
        database_executor=database_executor,
        table_executor=table_executor,
        table_registry=table_registry,
    ).bootstrap()

    assert database_executor.queries == [
        "CREATE DATABASE IF NOT EXISTS `cdc_sync_analytics`"
    ]
    assert "CREATE TABLE IF NOT EXISTS `cdc_sync_analytics`.`customers`" in table_executor.queries[0]
    assert "CREATE TABLE IF NOT EXISTS `cdc_sync_analytics`.`orders`" in table_executor.queries[1]
