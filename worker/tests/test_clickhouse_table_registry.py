import pytest

from clickhouse_table_registry import build_clickhouse_table_registry
from config import ClickHouseConfig

from .helpers import build_table_config


def test_build_table_registry_adds_technical_columns() -> None:
    registry = build_clickhouse_table_registry(
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
            )
        },
    )

    table = registry.get("customers")

    assert table.database == "cdc_sync_analytics"
    assert table.table_name == "customers"
    assert tuple(column.name for column in table.business_columns) == ("id", "email")
    assert tuple(column.name for column in table.technical_columns) == (
        "version",
        "deleted",
    )
    assert tuple(column.name for column in table.insert_columns) == (
        "id",
        "email",
        "version",
        "deleted",
    )


def test_create_table_query_uses_replacing_merge_tree_and_order_by_pk() -> None:
    registry = build_clickhouse_table_registry(
        ClickHouseConfig(
            host="clickhouse",
            port=9000,
            secure=False,
            database="cdc_sync_analytics",
            user="cdc_sync",
            password="cdc_sync",
        ),
        tables={
            "order_lines": build_table_config(
                table="order_lines",
                topic="cdc_sync.public.order_lines",
                primary_key_fields=("order_id", "line_id"),
                destination_columns=(
                    ("order_id", "UInt64", False),
                    ("line_id", "UInt64", False),
                    ("sku", "String", True),
                ),
            )
        },
    )

    query = registry.get("order_lines").create_table_query

    assert "CREATE TABLE IF NOT EXISTS `cdc_sync_analytics`.`order_lines`" in query
    assert "`sku` Nullable(String)" in query
    assert "`version` UInt64" in query
    assert "`deleted` UInt8" in query
    assert "ENGINE = ReplacingMergeTree(version)" in query
    assert "ORDER BY (`order_id`, `line_id`)" in query


def test_build_table_registry_skips_disabled_tables() -> None:
    registry = build_clickhouse_table_registry(
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
            ),
            "orders": build_table_config(
                table="orders",
                topic="cdc_sync.public.orders",
                primary_key_fields=("id",),
                enabled=False,
            ),
        },
    )

    assert tuple(registry.tables) == ("customers",)


def test_build_table_registry_allows_non_pk_column_not_nullable() -> None:
    registry = build_clickhouse_table_registry(
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
                    ("email", "String", False),
                ),
            )
        },
    )

    query = registry.get("customers").create_table_query

    assert "`email` String" in query


def test_delete_insert_query_uses_only_pk_and_technical_columns() -> None:
    registry = build_clickhouse_table_registry(
        ClickHouseConfig(
            host="clickhouse",
            port=9000,
            secure=False,
            database="cdc_sync_analytics",
            user="cdc_sync",
            password="cdc_sync",
        ),
        tables={
            "orders": build_table_config(
                table="orders",
                topic="cdc_sync.public.orders",
                primary_key_fields=("id",),
                destination_columns=(
                    ("id", "UInt64", False),
                    ("status", "String", False),
                    ("total_amount", "Decimal(10, 2)", False),
                ),
            )
        },
    )

    table = registry.get("orders")

    assert tuple(column.name for column in table.delete_insert_columns) == (
        "id",
        "version",
        "deleted",
    )
    assert (
        table.delete_insert_query
        == "INSERT INTO `cdc_sync_analytics`.`orders` (`id`, `version`, `deleted`) VALUES"
    )
