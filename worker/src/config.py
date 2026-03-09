from dataclasses import dataclass
from os import getenv

VALID_AUTO_OFFSET_RESET = {"earliest", "latest"}


@dataclass(frozen=True)
class WorkerConfig:
    kafka_bootstrap_servers: str
    kafka_topic_pattern: str
    kafka_group_id: str
    kafka_auto_offset_reset: str
    kafka_poll_timeout_ms: int


def load_config() -> WorkerConfig:
    kafka_bootstrap_servers = _read_required_env("WORKER_KAFKA_BOOTSTRAP_SERVERS")
    kafka_topic_pattern = _read_required_env("WORKER_KAFKA_TOPIC_PATTERN")
    kafka_group_id = _read_required_env("WORKER_KAFKA_GROUP_ID")
    kafka_auto_offset_reset = _read_required_env("WORKER_KAFKA_AUTO_OFFSET_RESET")
    kafka_poll_timeout_ms = _read_positive_int_env("WORKER_KAFKA_POLL_TIMEOUT_MS")

    if kafka_auto_offset_reset not in VALID_AUTO_OFFSET_RESET:
        raise ValueError(
            "WORKER_KAFKA_AUTO_OFFSET_RESET debe ser 'earliest' o 'latest'"
        )

    return WorkerConfig(
        kafka_bootstrap_servers=kafka_bootstrap_servers,
        kafka_topic_pattern=kafka_topic_pattern,
        kafka_group_id=kafka_group_id,
        kafka_auto_offset_reset=kafka_auto_offset_reset,
        kafka_poll_timeout_ms=kafka_poll_timeout_ms,
    )


def _read_required_env(name: str) -> str:
    value = getenv(name, "").strip()

    if not value:
        raise ValueError(f"La variable {name} es obligatoria")

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
