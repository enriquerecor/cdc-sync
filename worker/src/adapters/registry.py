from adapters.change_event_adapter import ChangeEventAdapter
from adapters.debezium_postgres_adapter import DebeziumPostgresAdapter

SUPPORTED_CHANGE_EVENT_ADAPTERS = ("debezium_postgres",)


def build_change_event_adapters() -> dict[str, ChangeEventAdapter]:
    return {
        SUPPORTED_CHANGE_EVENT_ADAPTERS[0]: DebeziumPostgresAdapter(),
    }


def supported_change_event_adapter_names() -> frozenset[str]:
    return frozenset(SUPPORTED_CHANGE_EVENT_ADAPTERS)
