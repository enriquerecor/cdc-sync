import base64
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID

from normalized_value import NormalizedValue


DEBEZIUM_DATE = "io.debezium.time.Date"
DEBEZIUM_ISO_DATE = "io.debezium.time.IsoDate"
DEBEZIUM_TIMESTAMP = "io.debezium.time.Timestamp"
DEBEZIUM_MICRO_TIMESTAMP = "io.debezium.time.MicroTimestamp"
DEBEZIUM_NANO_TIMESTAMP = "io.debezium.time.NanoTimestamp"
DEBEZIUM_ISO_TIMESTAMP = "io.debezium.time.IsoTimestamp"
DEBEZIUM_ZONED_TIMESTAMP = "io.debezium.time.ZonedTimestamp"
DEBEZIUM_UUID = "io.debezium.data.Uuid"
DEBEZIUM_JSON = "io.debezium.data.Json"
KAFKA_CONNECT_DATE = "org.apache.kafka.connect.data.Date"
KAFKA_CONNECT_TIMESTAMP = "org.apache.kafka.connect.data.Timestamp"
KAFKA_CONNECT_DECIMAL = "org.apache.kafka.connect.data.Decimal"


def normalize_debezium_data(
    data: dict[str, object],
    schema: dict[str, object],
) -> dict[str, NormalizedValue]:
    if _read_string(schema.get("type")) != "struct":
        raise ValueError("El schema de Debezium para la fila debe ser de tipo struct")

    field_schemas = _build_field_schema_map(schema)

    return {
        field_name: _normalize_field_value(field_name, field_schemas, field_value)
        for field_name, field_value in data.items()
    }


def _build_field_schema_map(schema: dict[str, object]) -> dict[str, dict[str, object]]:
    field_schemas: dict[str, dict[str, object]] = {}

    for field_schema in _read_list(schema.get("fields")):
        if not isinstance(field_schema, dict):
            continue

        field_name = _read_string(field_schema.get("field"))
        if field_name is None:
            continue

        field_schemas[field_name] = field_schema

    return field_schemas


def _normalize_field_value(
    field_name: str,
    field_schemas: dict[str, dict[str, object]],
    field_value: object,
) -> NormalizedValue:
    if field_value is None:
        return None

    try:
        field_schema = field_schemas[field_name]
    except KeyError as exc:
        raise ValueError(
            f"El schema de Debezium no incluye el campo '{field_name}'"
        ) from exc

    logical_type = _read_string(field_schema.get("name"))
    if logical_type in {DEBEZIUM_DATE, DEBEZIUM_ISO_DATE, KAFKA_CONNECT_DATE}:
        return _normalize_date(field_name, field_value, logical_type)

    if logical_type in {
        DEBEZIUM_TIMESTAMP,
        DEBEZIUM_MICRO_TIMESTAMP,
        DEBEZIUM_NANO_TIMESTAMP,
        DEBEZIUM_ISO_TIMESTAMP,
        KAFKA_CONNECT_TIMESTAMP,
    }:
        return _normalize_timestamp(field_name, field_value, logical_type)

    if logical_type == DEBEZIUM_ZONED_TIMESTAMP:
        return _normalize_zoned_timestamp(field_name, field_value)

    if logical_type == DEBEZIUM_UUID:
        return _normalize_uuid(field_name, field_value)

    if logical_type == DEBEZIUM_JSON:
        return _normalize_json(field_name, field_value)

    if logical_type == KAFKA_CONNECT_DECIMAL:
        return _normalize_decimal(field_name, field_schema, field_value)

    field_type = _read_string(field_schema.get("type"))
    if field_type == "boolean":
        return _normalize_boolean(field_name, field_value)

    if field_type == "bytes":
        return _normalize_bytes(field_name, field_value)

    if field_type == "struct" and isinstance(field_value, dict):
        return normalize_debezium_data(field_value, field_schema)

    return field_value


def _normalize_boolean(field_name: str, value: object) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, int) and value in {0, 1}:
        return bool(value)

    if isinstance(value, str):
        normalized_value = value.strip().lower()
        if normalized_value == "true":
            return True
        if normalized_value == "false":
            return False

    raise ValueError(f"El campo '{field_name}' debe ser un booleano Debezium valido")


def _normalize_date(
    field_name: str,
    value: object,
    logical_type: str,
) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if logical_type == DEBEZIUM_ISO_DATE:
        if not isinstance(value, str):
            raise ValueError(f"El campo '{field_name}' debe ser una fecha Debezium valida")

        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"El campo '{field_name}' debe ser una fecha Debezium valida"
            ) from exc

    if isinstance(value, int) and not isinstance(value, bool):
        return date(1970, 1, 1) + timedelta(days=value)

    raise ValueError(f"El campo '{field_name}' debe ser una fecha Debezium valida")


def _normalize_timestamp(
    field_name: str,
    value: object,
    logical_type: str,
) -> datetime:
    if isinstance(value, datetime):
        return _drop_timezone(value)

    if logical_type == DEBEZIUM_ISO_TIMESTAMP:
        if not isinstance(value, str):
            raise ValueError(
                f"El campo '{field_name}' debe ser un timestamp Debezium valido"
            )

        try:
            return _drop_timezone(datetime.fromisoformat(value))
        except ValueError as exc:
            raise ValueError(
                f"El campo '{field_name}' debe ser un timestamp Debezium valido"
            ) from exc

    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"El campo '{field_name}' debe ser un timestamp Debezium valido")

    if logical_type in {DEBEZIUM_TIMESTAMP, KAFKA_CONNECT_TIMESTAMP}:
        return datetime(1970, 1, 1) + timedelta(milliseconds=value)

    if logical_type == DEBEZIUM_MICRO_TIMESTAMP:
        return datetime(1970, 1, 1) + timedelta(microseconds=value)

    if logical_type == DEBEZIUM_NANO_TIMESTAMP:
        return datetime(1970, 1, 1) + timedelta(microseconds=value // 1_000)

    raise ValueError(f"El campo '{field_name}' debe ser un timestamp Debezium valido")


def _normalize_zoned_timestamp(field_name: str, value: object) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError(
                f"El campo '{field_name}' debe ser un ZonedTimestamp de Debezium valido"
            )

        return value

    if not isinstance(value, str):
        raise ValueError(
            f"El campo '{field_name}' debe ser un ZonedTimestamp de Debezium valido"
        )

    normalized_value = value.replace("Z", "+00:00")

    try:
        parsed_value = datetime.fromisoformat(normalized_value)
    except ValueError as exc:
        raise ValueError(
            f"El campo '{field_name}' debe ser un ZonedTimestamp de Debezium valido"
        ) from exc

    if parsed_value.tzinfo is None:
        raise ValueError(
            f"El campo '{field_name}' debe ser un ZonedTimestamp de Debezium valido"
        )

    return parsed_value


def _normalize_uuid(field_name: str, value: object) -> str:
    if not isinstance(value, str):
        raise ValueError(f"El campo '{field_name}' debe ser un UUID Debezium valido")

    try:
        return str(UUID(value))
    except ValueError as exc:
        raise ValueError(
            f"El campo '{field_name}' debe ser un UUID Debezium valido"
        ) from exc


def _normalize_json(field_name: str, value: object) -> NormalizedValue:
    if isinstance(value, str):
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"El campo '{field_name}' debe ser un JSON Debezium valido"
            ) from exc

        return _normalize_json_value(field_name, parsed_value)

    return _normalize_json_value(field_name, value)


def _normalize_decimal(
    field_name: str,
    field_schema: dict[str, object],
    value: object,
) -> Decimal:
    if isinstance(value, Decimal):
        return value

    scale = _read_decimal_scale(field_name, field_schema)

    if isinstance(value, (int, float, str)) and not isinstance(value, bool):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            pass

    raw_bytes = _read_decimal_bytes(field_name, value)
    integer_value = int.from_bytes(raw_bytes, byteorder="big", signed=True)
    return Decimal(integer_value).scaleb(-scale)


def _read_decimal_scale(field_name: str, field_schema: dict[str, object]) -> int:
    parameters = field_schema.get("parameters")
    if not isinstance(parameters, dict):
        raise ValueError(
            f"El campo decimal '{field_name}' debe incluir 'parameters.scale'"
        )

    scale = parameters.get("scale")
    if not isinstance(scale, str) or not scale.isdigit():
        raise ValueError(
            f"El campo decimal '{field_name}' debe incluir 'parameters.scale'"
        )

    return int(scale)


def _read_decimal_bytes(field_name: str, value: object) -> bytes:
    if isinstance(value, bytes):
        return value

    if isinstance(value, str):
        try:
            return base64.b64decode(value, validate=True)
        except ValueError as exc:
            raise ValueError(
                f"El campo decimal '{field_name}' debe contener bytes Debezium validos"
            ) from exc

    raise ValueError(
        f"El campo decimal '{field_name}' debe contener bytes Debezium validos"
    )


def _normalize_bytes(field_name: str, value: object) -> bytes:
    if isinstance(value, bytes):
        return value

    if isinstance(value, str):
        try:
            return base64.b64decode(value, validate=True)
        except ValueError as exc:
            raise ValueError(
                f"El campo '{field_name}' debe contener bytes Debezium validos"
            ) from exc

    raise ValueError(f"El campo '{field_name}' debe contener bytes Debezium validos")


def _normalize_json_value(field_name: str, value: object) -> NormalizedValue:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return value

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return [_normalize_json_value(field_name, item) for item in value]

    if isinstance(value, dict):
        normalized_object: dict[str, NormalizedValue] = {}
        for key, nested_value in value.items():
            if not isinstance(key, str):
                raise ValueError(
                    f"El campo '{field_name}' debe ser un JSON Debezium valido"
                )

            normalized_object[key] = _normalize_json_value(field_name, nested_value)

        return normalized_object

    raise ValueError(f"El campo '{field_name}' debe ser un JSON Debezium valido")


def _drop_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value

    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _read_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value

    return []


def _read_string(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value

    return None
