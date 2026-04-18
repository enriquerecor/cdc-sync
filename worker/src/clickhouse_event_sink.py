from dataclasses import dataclass

from clickhouse_client import ClickHouseRowWriter
from clickhouse_table_registry import ClickHouseColumn, ClickHouseTableDefinition, ClickHouseTableRegistry
from event_sink import EventSink
from normalized_event import NormalizedEvent


@dataclass(frozen=True)
class ClickHouseEventSink(EventSink):
    row_writer: ClickHouseRowWriter
    table_registry: ClickHouseTableRegistry

    def persist(self, event: NormalizedEvent) -> None:
        table = self.table_registry.get(event.table)
        if event.deleted:
            row = _build_delete_insert_row(table, event)
            self.row_writer.insert_rows(table.delete_insert_query, [row])
            return

        row = _build_upsert_insert_row(table, event)
        self.row_writer.insert_rows(table.insert_query, [row])


def _build_upsert_insert_row(
    table: ClickHouseTableDefinition,
    event: NormalizedEvent,
) -> dict[str, object]:
    row = {
        column.name: _resolve_upsert_column_value(column, event)
        for column in table.business_columns
    }
    row["version"] = event.version
    row["deleted"] = int(event.deleted)
    return row


def _build_delete_insert_row(
    table: ClickHouseTableDefinition,
    event: NormalizedEvent,
) -> object:
    row = {
        primary_key_name: _resolve_delete_primary_key_value(
            table,
            event,
            primary_key_name,
        )
        for primary_key_name in table.order_by_columns
    }
    row["version"] = event.version
    row["deleted"] = int(event.deleted)
    return row


def _resolve_upsert_column_value(
    column: ClickHouseColumn,
    event: NormalizedEvent,
) -> object:
    if column.name in event.data:
        return _validate_column_value(
            event.table,
            column,
            event.data[column.name],
        )

    if column.name in event.primary_key:
        return _validate_column_value(
            event.table,
            column,
            event.primary_key[column.name],
        )

    raise ValueError(
        f"El evento de la tabla '{event.table}' no incluye la columna configurada '{column.name}'"
    )


def _resolve_delete_primary_key_value(
    table: ClickHouseTableDefinition,
    event: NormalizedEvent,
    primary_key_name: str,
) -> object:
    try:
        return event.primary_key[primary_key_name]
    except KeyError as exc:
        raise ValueError(
            f"El delete de la tabla '{table.logical_name}' no incluye la PK '{primary_key_name}'"
        ) from exc


def _validate_column_value(
    table_name: str,
    column: ClickHouseColumn,
    value: object,
) -> object:
    if value is not None or column.nullable:
        return value

    raise ValueError(
        f"El evento de la tabla '{table_name}' incluye null en la columna no nullable '{column.name}'"
    )
