from datetime import date, datetime
from decimal import Decimal

import pytest

from normalized_value import validate_normalized_row


def test_validate_normalized_row_accepts_supported_types() -> None:
    row = validate_normalized_row(
        "customers",
        {
            "is_active": True,
            "birth_date": date(2026, 4, 11),
            "updated_at": datetime(2026, 4, 11, 19, 0, 0),
            "external_id": "4d36e967-e325-11ce-bfc1-08002be10318",
            "metadata": {"tags": ["vip", "beta"], "score": 7},
            "attachment": b"abc",
            "credit": Decimal("12.50"),
        },
        label="payload normalizado",
    )

    assert row["is_active"] is True
    assert row["birth_date"] == date(2026, 4, 11)
    assert row["updated_at"] == datetime(2026, 4, 11, 19, 0, 0)
    assert row["metadata"] == {"tags": ["vip", "beta"], "score": 7}
    assert row["attachment"] == b"abc"
    assert row["credit"] == Decimal("12.50")


def test_validate_normalized_row_fails_for_unsupported_type() -> None:
    with pytest.raises(
        TypeError,
        match="no pertenece al contrato interno de tipos normalizados",
    ):
        validate_normalized_row(
            "customers",
            {"invalid": {1, 2, 3}},
            label="payload normalizado",
        )
