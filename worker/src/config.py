from dataclasses import dataclass
from os import getenv

from table_config import TableConfig, load_table_registry

VALID_AUTO_OFFSET_RESET = {"earliest", "latest"}
DEFAULT_TABLE_CONFIG_PATH = "config/tables.json"
DEFAULT_CLICKHOUSE_HOST = "clickhouse"
DEFAULT_CLICKHOUSE_PORT = 9000
DEFAULT_CLICKHOUSE_DATABASE = "cdc_sync_analytics"
DEFAULT_CLICKHOUSE_USER = "cdc_sync"
DEFAULT_CLICKHOUSE_PASSWORD = "cdc_sync"


@dataclass(frozen=True)
class ClickHouseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str


@dataclass(frozen=True)
class WorkerConfig:
    kafka_bootstrap_servers: str
    kafka_topics: list[str]
    kafka_client_id: str
    kafka_group_id: str
    kafka_auto_offset_reset: str
    kafka_poll_timeout_ms: int
    table_config_path: str
    table_config_version: int
    tables: dict[str, TableConfig]
    clickhouse: ClickHouseConfig


def load_config() -> WorkerConfig:
    kafka_bootstrap_servers = _read_required_env("WORKER_KAFKA_BOOTSTRAP_SERVERS")
    kafka_client_id = _read_required_env("WORKER_KAFKA_CLIENT_ID")
    kafka_group_id = _read_required_env("WORKER_KAFKA_GROUP_ID")
    kafka_auto_offset_reset = _read_required_env("WORKER_KAFKA_AUTO_OFFSET_RESET")
    kafka_poll_timeout_ms = _read_positive_int_env("WORKER_KAFKA_POLL_TIMEOUT_MS")
    table_config_path = _read_optional_env(
        "WORKER_TABLE_CONFIG_PATH", DEFAULT_TABLE_CONFIG_PATH
    )
    clickhouse = ClickHouseConfig(
        host=_read_optional_env("WORKER_CLICKHOUSE_HOST", DEFAULT_CLICKHOUSE_HOST),
        port=_read_optional_positive_int_env(
            "WORKER_CLICKHOUSE_PORT", DEFAULT_CLICKHOUSE_PORT
        ),
        database=_read_optional_env(
            "WORKER_CLICKHOUSE_DB", DEFAULT_CLICKHOUSE_DATABASE
        ),
        user=_read_optional_env("WORKER_CLICKHOUSE_USER", DEFAULT_CLICKHOUSE_USER),
        password=_read_optional_env(
            "WORKER_CLICKHOUSE_PASSWORD", DEFAULT_CLICKHOUSE_PASSWORD
        ),
    )
    table_registry = load_table_registry(table_config_path)
    kafka_topics = _build_kafka_topics(table_registry.tables)

    if kafka_auto_offset_reset not in VALID_AUTO_OFFSET_RESET:
        raise ValueError(
            "WORKER_KAFKA_AUTO_OFFSET_RESET debe ser 'earliest' o 'latest'"
        )

    return WorkerConfig(
        kafka_bootstrap_servers=kafka_bootstrap_servers,
        kafka_topics=kafka_topics,
        kafka_client_id=kafka_client_id,
        kafka_group_id=kafka_group_id,
        kafka_auto_offset_reset=kafka_auto_offset_reset,
        kafka_poll_timeout_ms=kafka_poll_timeout_ms,
        table_config_path=table_config_path,
        table_config_version=table_registry.version,
        tables=table_registry.tables,
        clickhouse=clickhouse,
    )


def _read_required_env(name: str) -> str:
    value = getenv(name, "").strip()

    if not value:
        raise ValueError(f"La variable {name} es obligatoria")

    return value


def _read_optional_env(name: str, default: str) -> str:
    value = getenv(name, default).strip()

    if not value:
        raise ValueError(f"La variable {name} no puede estar vacia")

    return value


def _read_positive_int_env(name: str) -> int:
    raw_value = _read_required_env(name)
    return _parse_positive_int(raw_value, name)


def _read_optional_positive_int_env(name: str, default: int) -> int:
    raw_value = _read_optional_env(name, str(default))
    return _parse_positive_int(raw_value, name)


def _parse_positive_int(raw_value: str, name: str) -> int:
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"La variable {name} debe ser un entero") from exc

    if value <= 0:
        raise ValueError(f"La variable {name} debe ser mayor que 0")

    return value


def _build_kafka_topics(tables: dict[str, TableConfig]) -> list[str]:
    topics: list[str] = []
    seen_topics: set[str] = set()

    for table_config in tables.values():
        if not table_config.enabled:
            continue

        topic = table_config.source.topic
        if not topic or topic in seen_topics:
            continue

        seen_topics.add(topic)
        topics.append(topic)

    if not topics:
        raise ValueError(
            "La configuracion debe incluir al menos una tabla habilitada con 'source.topic'"
        )

    return topics
