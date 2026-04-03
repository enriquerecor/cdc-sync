from adapters.change_event_adapter import ChangeEventAdapter
from normalized_event import Operation


class DebeziumPostgresAdapter(ChangeEventAdapter):
    def is_tombstone(self, value: object) -> bool:
        return value is None

    def extract_table_name(self, topic: str, value: dict[str, object]) -> str:
        payload = _read_dict(value.get("payload"))
        source = _read_dict(payload.get("source"))
        table_name = _read_string(source.get("table"))

        if table_name is not None:
            return table_name

        return _extract_table_name_from_topic(topic)

    def extract_operation(self, value: dict[str, object]) -> Operation:
        payload = _read_dict(value.get("payload"))
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
        payload = _read_dict(value.get("payload"))
        payload_field = _DATA_FIELD_BY_OPERATION[operation]
        data = payload.get(payload_field)

        if not isinstance(data, dict):
            raise ValueError(
                f"El payload de Debezium debe incluir '{payload_field}' para la "
                f"operacion {operation.value}"
            )

        return data

    def extract_version(self, value: dict[str, object]) -> int:
        payload = _read_dict(value.get("payload"))
        source = _read_dict(payload.get("source"))
        lsn = source.get("lsn")

        if not isinstance(lsn, int) or isinstance(lsn, bool):
            raise ValueError(
                "El payload de Debezium PostgreSQL debe incluir 'source.lsn' como entero"
            )

        return lsn


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


def _read_string(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value

    return None
