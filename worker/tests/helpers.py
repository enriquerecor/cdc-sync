from typing import Any

from table_config import (
    TableConfig,
    TableDestinationColumnConfig,
    TableDestinationConfig,
    TableSourceConfig,
    TableSyncConfig,
)


def build_table_config(
    table: str,
    topic: str,
    primary_key_fields: tuple[str, ...],
    adapter: str = "debezium_postgres",
) -> TableConfig:
    destination_columns = tuple(
        TableDestinationColumnConfig(
            name=field_name,
            type="UInt64",
            nullable=False,
        )
        for field_name in primary_key_fields
    )

    return TableConfig(
        enabled=True,
        source=TableSourceConfig(
            adapter=adapter,
            table=table,
            topic=topic,
            connection="postgres_local",
            schema="public",
        ),
        primary_key_fields=primary_key_fields,
        sync=TableSyncConfig(mode="realtime"),
        destination=TableDestinationConfig(
            table=table,
            columns=destination_columns,
        ),
    )


def build_debezium_event(
    *,
    operation: str,
    table: str,
    lsn: int | None,
    after: dict[str, object] | None = None,
    before: dict[str, object] | None = None,
) -> dict[str, Any]:
    source: dict[str, Any] = {"table": table}
    if lsn is not None:
        source["lsn"] = lsn

    return {
        "payload": {
            "op": operation,
            "before": before,
            "after": after,
            "source": source,
        }
    }
