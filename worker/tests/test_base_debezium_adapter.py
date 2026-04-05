import pytest

from adapters.base_debezium_adapter import BaseDebeziumAdapter
from normalized_event import Operation

from .helpers import build_debezium_event


class FakeDebeziumAdapter(BaseDebeziumAdapter):
    def extract_version(self, value: dict[str, object]) -> int:
        return 1

    def extract_source_position(self, value: dict[str, object]) -> dict[str, object]:
        return {"offset": 1}


def test_extract_table_name_uses_source_table() -> None:
    adapter = FakeDebeziumAdapter()

    table_name = adapter.extract_table_name(
        "cdc_sync.public.fallback",
        build_debezium_event(operation="c", table="customers", lsn=101),
    )

    assert table_name == "customers"


def test_extract_table_name_falls_back_to_topic() -> None:
    adapter = FakeDebeziumAdapter()

    table_name = adapter.extract_table_name(
        "cdc_sync.public.customers",
        {"payload": {"source": {}}},
    )

    assert table_name == "customers"


def test_extract_operation_maps_debezium_codes() -> None:
    adapter = FakeDebeziumAdapter()

    operation = adapter.extract_operation(
        build_debezium_event(operation="r", table="customers", lsn=101)
    )

    assert operation is Operation.SNAPSHOT


def test_extract_data_uses_before_for_delete() -> None:
    adapter = FakeDebeziumAdapter()

    data = adapter.extract_data(
        build_debezium_event(
            operation="d",
            table="orders",
            lsn=202,
            before={"id": 3, "status": "cancelled"},
        ),
        Operation.DELETE,
    )

    assert data == {"id": 3, "status": "cancelled"}


def test_extract_operation_fails_for_unsupported_code() -> None:
    adapter = FakeDebeziumAdapter()

    with pytest.raises(ValueError, match="Operacion de Debezium no soportada: x"):
        adapter.extract_operation({"payload": {"op": "x"}})
