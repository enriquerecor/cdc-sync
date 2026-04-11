from adapters.change_event_adapter import ChangeEventAdapter
from adapters.debezium_postgres_adapter import DebeziumPostgresAdapter


def build_change_event_adapters() -> dict[str, ChangeEventAdapter]:
    return {
        "debezium_postgres": DebeziumPostgresAdapter(),
    }
