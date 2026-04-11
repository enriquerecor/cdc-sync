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
    destination_columns: tuple[tuple[str, str, bool], ...] | None = None,
    enabled: bool = True,
) -> TableConfig:
    resolved_destination_columns = destination_columns
    if resolved_destination_columns is None:
        resolved_destination_columns = tuple(
            (field_name, "UInt64", False)
            for field_name in primary_key_fields
        )

    return TableConfig(
        enabled=enabled,
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
            columns=tuple(
                TableDestinationColumnConfig(
                    name=name,
                    type=column_type,
                    nullable=nullable,
                )
                for name, column_type, nullable in resolved_destination_columns
            ),
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
