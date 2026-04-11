from dataclasses import dataclass
from os import getenv

from table_config import TableConfig, load_table_registry

VALID_AUTO_OFFSET_RESET = {"earliest", "latest"}
DEFAULT_TABLE_CONFIG_PATH = "config/tables.json"


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


def load_config() -> WorkerConfig:
    kafka_bootstrap_servers = _read_required_env("WORKER_KAFKA_BOOTSTRAP_SERVERS")
    kafka_client_id = _read_required_env("WORKER_KAFKA_CLIENT_ID")
    kafka_group_id = _read_required_env("WORKER_KAFKA_GROUP_ID")
    kafka_auto_offset_reset = _read_required_env("WORKER_KAFKA_AUTO_OFFSET_RESET")
    kafka_poll_timeout_ms = _read_positive_int_env("WORKER_KAFKA_POLL_TIMEOUT_MS")
    table_config_path = _read_optional_env(
        "WORKER_TABLE_CONFIG_PATH", DEFAULT_TABLE_CONFIG_PATH
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
