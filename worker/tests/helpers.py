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
            schema="public",
            table=table,
            topic=topic,
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
    after_schema_fields: list[dict[str, object]] | None = None,
    before_schema_fields: list[dict[str, object]] | None = None,
) -> dict[str, Any]:
    source: dict[str, Any] = {"table": table}
    if lsn is not None:
        source["lsn"] = lsn

    event: dict[str, Any] = {
        "payload": {
            "op": operation,
            "before": before,
            "after": after,
            "source": source,
        }
    }

    schema_fields: list[dict[str, object]] = []
    if before_schema_fields is not None:
        schema_fields.append(
            {
                "type": "struct",
                "fields": before_schema_fields,
                "optional": True,
                "field": "before",
            }
        )

    if after_schema_fields is not None:
        schema_fields.append(
            {
                "type": "struct",
                "fields": after_schema_fields,
                "optional": True,
                "field": "after",
            }
        )

    if schema_fields:
        event["schema"] = {
            "type": "struct",
            "fields": schema_fields,
        }

    return event
