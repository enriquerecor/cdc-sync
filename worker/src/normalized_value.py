from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TypeAlias


NormalizedScalar: TypeAlias = (
    None | bool | int | float | str | Decimal | date | datetime | bytes
)
NormalizedValue: TypeAlias = (
    NormalizedScalar
    | list["NormalizedValue"]
    | dict[str, "NormalizedValue"]
)
NormalizedRow: TypeAlias = dict[str, NormalizedValue]


def validate_normalized_row(
    table_name: str,
    row: dict[str, object],
    *,
    label: str,
) -> NormalizedRow:
    validated_row: NormalizedRow = {}

    for field_name, field_value in row.items():
        if not isinstance(field_name, str):
            raise TypeError(
                f"El {label} de la tabla '{table_name}' contiene una clave no valida"
            )

        validated_row[field_name] = _validate_normalized_value(
            table_name=table_name,
            value=field_value,
            path=f"{label}.{field_name}",
        )

    return validated_row


def _validate_normalized_value(
    *,
    table_name: str,
    value: object,
    path: str,
) -> NormalizedValue:
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

    if isinstance(value, Decimal):
        return value

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return value

    if isinstance(value, bytes):
        return value

    if isinstance(value, list):
        return [
            _validate_normalized_value(
                table_name=table_name,
                value=item,
                path=f"{path}[{index}]",
            )
            for index, item in enumerate(value)
        ]

    if isinstance(value, dict):
        normalized_object: dict[str, NormalizedValue] = {}
        for nested_key, nested_value in value.items():
            if not isinstance(nested_key, str):
                raise TypeError(
                    f"El {path} de la tabla '{table_name}' contiene una clave no valida"
                )

            normalized_object[nested_key] = _validate_normalized_value(
                table_name=table_name,
                value=nested_value,
                path=f"{path}.{nested_key}",
            )

        return normalized_object

    raise TypeError(
        f"El {path} de la tabla '{table_name}' no pertenece al contrato interno de tipos normalizados"
    )
