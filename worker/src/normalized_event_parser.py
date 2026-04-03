from dataclasses import dataclass

from adapters.change_event_adapter import ChangeEventAdapter
from normalized_event import NormalizedEvent, Operation
from table_config import TableConfig


@dataclass(frozen=True)
class NormalizedEventParser:
    adapter: ChangeEventAdapter
    tables: dict[str, TableConfig]

    def parse(
        self, topic: str, value: dict[str, object] | None
    ) -> NormalizedEvent | None:
        if self.adapter.is_tombstone(value):
            return None

        if not isinstance(value, dict):
            raise TypeError("El valor del evento debe ser un objeto JSON")

        table_name = self.adapter.extract_table_name(topic, value)
        operation = self.adapter.extract_operation(value)
        data = self.adapter.extract_data(value, operation)

        return NormalizedEvent(
            table=table_name,
            primary_key=self._extract_primary_key(table_name, data),
            data=data,
            version=self.adapter.extract_version(value),
            deleted=operation is Operation.DELETE,
            operation=operation,
        )

    def _extract_primary_key(
        self, table_name: str, data: dict[str, object]
    ) -> dict[str, object]:
        table_config = self._get_table_config(table_name)

        primary_key: dict[str, object] = {}
        for field_name in table_config.primary_key_fields:
            if field_name not in data:
                raise ValueError(
                    f"Falta el campo de PK '{field_name}' en los datos de la tabla "
                    f"'{table_name}'"
                )

            primary_key[field_name] = data[field_name]

        return primary_key

    def _get_table_config(self, table_name: str) -> TableConfig:
        try:
            return self.tables[table_name]
        except KeyError as exc:
            raise ValueError(f"La tabla '{table_name}' no existe en la configuracion") from exc
