from typing import Any

from table_config import TableConfig, TableSourceConfig, TableSyncConfig


def build_table_config(
    table: str, topic: str, primary_key_fields: tuple[str, ...]
) -> TableConfig:
    return TableConfig(
        enabled=True,
        source=TableSourceConfig(
            adapter="debezium_postgres",
            table=table,
            topic=topic,
            connection="postgres_local",
            schema="public",
        ),
        primary_key_fields=primary_key_fields,
        sync=TableSyncConfig(mode="realtime"),
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
