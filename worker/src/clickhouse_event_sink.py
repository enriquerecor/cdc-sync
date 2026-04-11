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
        row = _build_insert_row(table, event)
        self.row_writer.insert_rows(table.insert_query, [row])


def _build_insert_row(
    table: ClickHouseTableDefinition,
    event: NormalizedEvent,
) -> dict[str, object]:
    row = {
        column.name: _resolve_column_value(column, table, event)
        for column in table.business_columns
    }
    row["version"] = event.version
    row["deleted"] = int(event.deleted)
    return row


def _resolve_column_value(
    column: ClickHouseColumn,
    table: ClickHouseTableDefinition,
    event: NormalizedEvent,
) -> object:
    if event.deleted:
        return _resolve_delete_column_value(column, table, event)

    return _resolve_upsert_column_value(column, event)


def _resolve_delete_column_value(
    column: ClickHouseColumn,
    table: ClickHouseTableDefinition,
    event: NormalizedEvent,
) -> object:
    if column.name in event.primary_key:
        return event.primary_key[column.name]

    if column.name in table.order_by_columns:
        raise ValueError(
            f"El delete de la tabla '{table.logical_name}' no incluye la PK '{column.name}'"
        )

    if not column.nullable:
        raise ValueError(
            f"La tabla '{table.logical_name}' define la columna no PK '{column.name}' como no nullable, "
            "pero el delete logico requiere columnas no PK nullable"
        )

    return None


def _resolve_upsert_column_value(
    column: ClickHouseColumn,
    event: NormalizedEvent,
) -> object:
    if column.name in event.data:
        return event.data[column.name]

    if column.name in event.primary_key:
        return event.primary_key[column.name]

    if column.nullable:
        return None

    raise ValueError(
        f"El evento de la tabla '{event.table}' no incluye la columna no nullable '{column.name}'"
    )
