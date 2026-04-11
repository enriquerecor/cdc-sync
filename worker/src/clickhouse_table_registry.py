from dataclasses import dataclass

from config import ClickHouseConfig
from table_config import TableConfig, TableDestinationColumnConfig


TECHNICAL_COLUMNS: tuple[tuple[str, str], ...] = (
    ("version", "UInt64"),
    ("deleted", "UInt8"),
)


@dataclass(frozen=True)
class ClickHouseColumn:
    name: str
    type: str
    nullable: bool

    @property
    def ddl_type(self) -> str:
        if self.nullable:
            return f"Nullable({self.type})"

        return self.type


@dataclass(frozen=True)
class ClickHouseTableDefinition:
    logical_name: str
    database: str
    table_name: str
    business_columns: tuple[ClickHouseColumn, ...]
    technical_columns: tuple[ClickHouseColumn, ...]
    order_by_columns: tuple[str, ...]

    @property
    def qualified_name(self) -> str:
        return f"{_quote_identifier(self.database)}.{_quote_identifier(self.table_name)}"

    @property
    def insert_columns(self) -> tuple[ClickHouseColumn, ...]:
        return self.business_columns + self.technical_columns

    @property
    def insert_column_names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.insert_columns)

    @property
    def insert_query(self) -> str:
        insert_columns = ", ".join(
            _quote_identifier(column_name)
            for column_name in self.insert_column_names
        )

        return (
            f"INSERT INTO {self.qualified_name} "
            f"({insert_columns}) VALUES"
        )

    @property
    def create_table_query(self) -> str:
        column_lines = [
            f"    {_quote_identifier(column.name)} {column.ddl_type}"
            for column in self.insert_columns
        ]
        column_definitions = ",\n".join(column_lines)
        order_by_expression = ", ".join(
            _quote_identifier(column_name) for column_name in self.order_by_columns
        )

        return (
            f"CREATE TABLE IF NOT EXISTS {self.qualified_name}\n"
            "(\n"
            f"{column_definitions}\n"
            ")\n"
            "ENGINE = ReplacingMergeTree(version)\n"
            f"ORDER BY ({order_by_expression})"
        )


@dataclass(frozen=True)
class ClickHouseTableRegistry:
    database: str
    tables: dict[str, ClickHouseTableDefinition]

    def get(self, logical_table_name: str) -> ClickHouseTableDefinition:
        try:
            return self.tables[logical_table_name]
        except KeyError as exc:
            raise ValueError(
                f"La tabla logica '{logical_table_name}' no existe en el registro de ClickHouse"
            ) from exc


def build_clickhouse_table_registry(
    clickhouse_config: ClickHouseConfig,
    tables: dict[str, TableConfig],
) -> ClickHouseTableRegistry:
    return ClickHouseTableRegistry(
        database=clickhouse_config.database,
        tables={
            logical_name: _build_table_definition(
                logical_name,
                clickhouse_config.database,
                table_config,
            )
            for logical_name, table_config in tables.items()
            if table_config.enabled
        },
    )


def _build_table_definition(
    logical_name: str,
    database: str,
    table_config: TableConfig,
) -> ClickHouseTableDefinition:
    business_columns = tuple(
        _build_business_column(column)
        for column in table_config.destination.columns
    )
    technical_columns = tuple(
        ClickHouseColumn(name=name, type=column_type, nullable=False)
        for name, column_type in TECHNICAL_COLUMNS
    )
    _validate_delete_compatibility(
        logical_name=logical_name,
        primary_key_fields=table_config.primary_key_fields,
        business_columns=business_columns,
    )

    return ClickHouseTableDefinition(
        logical_name=logical_name,
        database=database,
        table_name=table_config.destination.table,
        business_columns=business_columns,
        technical_columns=technical_columns,
        order_by_columns=table_config.primary_key_fields,
    )


def _build_business_column(
    column: TableDestinationColumnConfig,
) -> ClickHouseColumn:
    return ClickHouseColumn(
        name=column.name,
        type=column.type,
        nullable=column.nullable,
    )


def _validate_delete_compatibility(
    logical_name: str,
    primary_key_fields: tuple[str, ...],
    business_columns: tuple[ClickHouseColumn, ...],
) -> None:
    primary_key_field_set = set(primary_key_fields)

    for column in business_columns:
        if column.name in primary_key_field_set:
            continue

        if column.nullable:
            continue

        raise ValueError(
            f"La tabla '{logical_name}' define la columna no PK '{column.name}' como no nullable, "
            "pero el delete logico de ClickHouse en esta fase requiere columnas no PK nullable"
        )


def _quote_identifier(identifier: str) -> str:
    escaped_identifier = identifier.replace("`", "``")
    return f"`{escaped_identifier}`"
