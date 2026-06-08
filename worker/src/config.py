from dataclasses import dataclass
from os import getenv
from urllib.parse import urlparse
import warnings

from table_config import TableConfig, load_table_registry

VALID_AUTO_OFFSET_RESET = {"earliest", "latest"}
VALID_TRUE_ENV_VALUES = {"1", "true", "yes", "on"}
VALID_FALSE_ENV_VALUES = {"0", "false", "no", "off"}
COMMON_INSECURE_CLICKHOUSE_PORT = 9000
COMMON_SECURE_CLICKHOUSE_PORTS = frozenset({8443, 9440})
DEFAULT_TABLE_CONFIG_PATH = "config/tables.json"
DEFAULT_CLICKHOUSE_HOST = "clickhouse"
DEFAULT_CLICKHOUSE_PORT = 9000
DEFAULT_CLICKHOUSE_SECURE = False
DEFAULT_CLICKHOUSE_DATABASE = "cdc_sync_analytics"
DEFAULT_CLICKHOUSE_USER = "cdc_sync"
DEFAULT_CLICKHOUSE_PASSWORD = "cdc_sync"


@dataclass(frozen=True)
class ClickHouseConfig:
    host: str
    port: int
    secure: bool
    database: str
    user: str
    password: str


@dataclass(frozen=True)
class WorkerConfig:
    worker_id: str
    control_plane_base_url: str
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
    worker_id = _read_required_env("WORKER_ID")
    control_plane_base_url = _read_url_env("WORKER_CONTROL_PLANE_BASE_URL")
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
        secure=_read_optional_bool_env(
            "WORKER_CLICKHOUSE_SECURE",
            default=DEFAULT_CLICKHOUSE_SECURE,
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

    _warn_if_clickhouse_security_port_combo_is_suspicious(clickhouse)

    return WorkerConfig(
        worker_id=worker_id,
        control_plane_base_url=control_plane_base_url,
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


def _read_url_env(name: str) -> str:
    value = _read_required_env(name)
    parsed_url = urlparse(value)

    if parsed_url.scheme and parsed_url.netloc:
        return value

    raise ValueError(f"La variable {name} debe ser una URL con esquema y host")


def _read_optional_positive_int_env(name: str, default: int) -> int:
    raw_value = _read_optional_env(name, str(default))
    return _parse_positive_int(raw_value, name)


def _read_optional_bool_env(name: str, default: bool) -> bool:
    raw_value = getenv(name)

    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()

    if not normalized_value:
        raise ValueError(f"La variable {name} no puede estar vacia")

    if normalized_value in VALID_TRUE_ENV_VALUES:
        return True

    if normalized_value in VALID_FALSE_ENV_VALUES:
        return False

    raise ValueError(
        f"La variable {name} debe ser un booleano válido ({', '.join(sorted(VALID_TRUE_ENV_VALUES | VALID_FALSE_ENV_VALUES))})"
    )


def _parse_positive_int(raw_value: str, name: str) -> int:
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"La variable {name} debe ser un entero") from exc

    if value <= 0:
        raise ValueError(f"La variable {name} debe ser mayor que 0")

    return value


def _warn_if_clickhouse_security_port_combo_is_suspicious(
    clickhouse: ClickHouseConfig,
) -> None:
    if clickhouse.secure and clickhouse.port == COMMON_INSECURE_CLICKHOUSE_PORT:
        warnings.warn(
            "WORKER_CLICKHOUSE_SECURE=true con WORKER_CLICKHOUSE_PORT=9000 es una combinación no habitual. "
            "Para el entorno local usa 9000/false y para ClickHouse Cloud 9440/true.",
            UserWarning,
            stacklevel=2,
        )
        return

    if clickhouse.secure or clickhouse.port not in COMMON_SECURE_CLICKHOUSE_PORTS:
        return

    warnings.warn(
        f"WORKER_CLICKHOUSE_PORT={clickhouse.port} suele requerir WORKER_CLICKHOUSE_SECURE=true. "
        "Revisa la configuración si el destino es ClickHouse Cloud.",
        UserWarning,
        stacklevel=2,
    )


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
            "La configuración debe incluir al menos una tabla habilitada con 'source.topic'"
        )

    return topics
