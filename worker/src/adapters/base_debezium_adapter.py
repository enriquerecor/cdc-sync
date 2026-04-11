from abc import ABC, abstractmethod

from adapters.debezium_data_normalizer import normalize_debezium_data
from normalized_event import Operation


class BaseDebeziumAdapter(ABC):
    def is_tombstone(self, value: object) -> bool:
        return value is None

    def extract_table_name(self, topic: str, value: dict[str, object]) -> str:
        payload = self._read_payload(value)
        source = self._read_source(payload)
        table_name = _read_string(source.get("table"))

        if table_name is not None:
            return table_name

        return _extract_table_name_from_topic(topic)

    def extract_operation(self, value: dict[str, object]) -> Operation:
        payload = self._read_payload(value)
        raw_operation = _read_string(payload.get("op"))

        if raw_operation is None:
            raise ValueError("El payload de Debezium debe incluir 'op'")

        try:
            return _OPERATION_MAP[raw_operation]
        except KeyError as exc:
            raise ValueError(f"Operacion de Debezium no soportada: {raw_operation}") from exc

    def extract_data(
        self, value: dict[str, object], operation: Operation
    ) -> dict[str, object]:
        payload = self._read_payload(value)
        payload_field = _DATA_FIELD_BY_OPERATION[operation]
        data = payload.get(payload_field)

        if not isinstance(data, dict):
            raise ValueError(
                f"El payload de Debezium debe incluir '{payload_field}' para la "
                f"operacion {operation.value}"
            )

        data_schema = self._read_data_schema(value, payload_field)
        if data_schema is None:
            return data

        return normalize_debezium_data(data, data_schema)

    @abstractmethod
    def extract_version(self, value: dict[str, object]) -> int:
        """Resolve a comparable version value for the normalized event."""

    @abstractmethod
    def extract_source_position(self, value: dict[str, object]) -> dict[str, object]:
        """Expose source-specific position metadata for tracing and future adapters."""

    def _read_payload(self, value: dict[str, object]) -> dict[str, object]:
        return _read_dict(value.get("payload"))

    def _read_source(self, payload: dict[str, object]) -> dict[str, object]:
        return _read_dict(payload.get("source"))

    def _read_data_schema(
        self,
        value: dict[str, object],
        payload_field: str,
    ) -> dict[str, object] | None:
        envelope_schema = _read_dict(value.get("schema"))
        if not envelope_schema:
            return None

        for field_schema in _read_list(envelope_schema.get("fields")):
            if not isinstance(field_schema, dict):
                continue

            if field_schema.get("field") == payload_field:
                return field_schema

        return None


_OPERATION_MAP = {
    "c": Operation.INSERT,
    "u": Operation.UPDATE,
    "d": Operation.DELETE,
    "r": Operation.SNAPSHOT,
}

_DATA_FIELD_BY_OPERATION = {
    Operation.INSERT: "after",
    Operation.UPDATE: "after",
    Operation.DELETE: "before",
    Operation.SNAPSHOT: "after",
}


def _extract_table_name_from_topic(topic: str) -> str:
    parts = [part for part in topic.split(".") if part]
    if not parts:
        raise ValueError("El topic de Kafka debe incluir un nombre de tabla")

    return parts[-1]


def _read_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value

    return {}


def _read_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value

    return []


def _read_string(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value

    return None
