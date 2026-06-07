from collections.abc import Callable
from dataclasses import dataclass
from os import getenv
from urllib.parse import urlparse
import warnings

from adapters.registry import supported_change_event_adapter_names
from control_plane_client import fetch_worker_runtime_config
from table_config import TableConfig, build_table_configs_from_runtime

RUNTIME_CONTRACT_VERSION = 1
CLICKHOUSE_RUNTIME_ADAPTER = "clickhouse"
VALID_AUTO_OFFSET_RESET = {"earliest", "latest"}
VALID_SYNC_MODES = {"realtime"}
COMMON_INSECURE_CLICKHOUSE_PORT = 9000
COMMON_SECURE_CLICKHOUSE_PORTS = frozenset({8443, 9440})

RuntimeConfigFetcher = Callable[[str, str], dict[object, object]]


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
    runtime_contract_version: int
    kafka_bootstrap_servers: str
    kafka_topics: list[str]
    kafka_client_id: str
    kafka_group_id: str
    kafka_auto_offset_reset: str
    kafka_poll_timeout_ms: int
    tables: dict[str, TableConfig]
    clickhouse: ClickHouseConfig


def load_config(
    runtime_config_fetcher: RuntimeConfigFetcher = fetch_worker_runtime_config,
) -> WorkerConfig:
    worker_id = _read_required_env("WORKER_ID")
    control_plane_base_url = _read_url_env("WORKER_CONTROL_PLANE_BASE_URL")
    runtime_config = runtime_config_fetcher(control_plane_base_url, worker_id)

    return build_config_from_runtime(
        worker_id=worker_id,
        control_plane_base_url=control_plane_base_url,
        runtime_config=runtime_config,
    )


def build_config_from_runtime(
    *,
    worker_id: str,
    control_plane_base_url: str,
    runtime_config: object,
) -> WorkerConfig:
    root_config = _expect_dict(runtime_config, "La configuración runtime")
    contract_version = _contract_version(root_config)
    _ensure_supported_contract_version(contract_version)
    _ensure_worker_identity(root_config, worker_id)

    tables = build_table_configs_from_runtime(
        _required_value(root_config, "tables", "La configuración runtime")
    )
    _validate_runtime_tables(tables)
    kafka_config = _expect_dict(
        _required_value(root_config, "kafka", "La configuración runtime"),
        "La configuración runtime.kafka",
    )
    clickhouse = _build_clickhouse_config(
        _required_value(root_config, "destination", "La configuración runtime")
    )
    kafka_topics = _build_kafka_topics(kafka_config, tables)
    kafka_auto_offset_reset = _expect_non_empty_str(
        _required_value(
            kafka_config,
            "auto_offset_reset",
            "La configuración runtime.kafka",
        ),
        "La configuración runtime.kafka.auto_offset_reset",
    )

    if kafka_auto_offset_reset not in VALID_AUTO_OFFSET_RESET:
        raise ValueError(
            "La configuración runtime.kafka.auto_offset_reset debe ser 'earliest' o 'latest'"
        )

    _warn_if_clickhouse_security_port_combo_is_suspicious(clickhouse)

    return WorkerConfig(
        worker_id=worker_id,
        control_plane_base_url=control_plane_base_url,
        runtime_contract_version=contract_version,
        kafka_bootstrap_servers=_expect_non_empty_str(
            _required_value(
                kafka_config,
                "bootstrap_servers",
                "La configuración runtime.kafka",
            ),
            "La configuración runtime.kafka.bootstrap_servers",
        ),
        kafka_topics=kafka_topics,
        kafka_client_id=_expect_non_empty_str(
            _required_value(kafka_config, "client_id", "La configuración runtime.kafka"),
            "La configuración runtime.kafka.client_id",
        ),
        kafka_group_id=_expect_non_empty_str(
            _required_value(kafka_config, "group_id", "La configuración runtime.kafka"),
            "La configuración runtime.kafka.group_id",
        ),
        kafka_auto_offset_reset=kafka_auto_offset_reset,
        kafka_poll_timeout_ms=_expect_positive_int(
            _required_value(
                kafka_config,
                "poll_timeout_ms",
                "La configuración runtime.kafka",
            ),
            "La configuración runtime.kafka.poll_timeout_ms",
        ),
        tables=tables,
        clickhouse=clickhouse,
    )


def _read_required_env(name: str) -> str:
    value = getenv(name, "").strip()

    if not value:
        raise ValueError(f"La variable {name} es obligatoria")

    return value


def _read_url_env(name: str) -> str:
    value = _read_required_env(name)
    parsed_url = urlparse(value)

    if parsed_url.scheme and parsed_url.netloc:
        return value

    raise ValueError(f"La variable {name} debe ser una URL con esquema y host")


def _contract_version(root_config: dict[object, object]) -> int:
    return _expect_int(
        _required_value(root_config, "contract_version", "La configuración runtime"),
        "La configuración runtime.contract_version",
    )


def _ensure_supported_contract_version(contract_version: int) -> None:
    if contract_version == RUNTIME_CONTRACT_VERSION:
        return

    raise ValueError(
        "La configuración runtime usa una versión de contrato no soportada: "
        f"{contract_version}"
    )


def _ensure_worker_identity(
    root_config: dict[object, object],
    expected_worker_id: str,
) -> None:
    worker_config = _expect_dict(
        _required_value(root_config, "worker", "La configuración runtime"),
        "La configuración runtime.worker",
    )
    runtime_worker_id = _expect_non_empty_str(
        _required_value(worker_config, "worker_id", "La configuración runtime.worker"),
        "La configuración runtime.worker.worker_id",
    )

    if runtime_worker_id == expected_worker_id:
        return

    raise ValueError(
        "La configuración runtime pertenece al worker "
        f"'{runtime_worker_id}', pero el proceso arrancó como '{expected_worker_id}'"
    )


def _validate_runtime_tables(tables: dict[str, TableConfig]) -> None:
    if not tables:
        raise ValueError(
            "La configuración runtime debe incluir al menos una tabla habilitada"
        )

    for table_name, table_config in tables.items():
        _ensure_table_enabled(table_name, table_config)
        _ensure_table_source_adapter(table_name, table_config)
        _ensure_table_sync_mode(table_name, table_config)


def _ensure_table_enabled(table_name: str, table_config: TableConfig) -> None:
    if table_config.enabled:
        return

    raise ValueError(
        f"La tabla runtime '{table_name}' no puede estar deshabilitada en el worker"
    )


def _ensure_table_source_adapter(table_name: str, table_config: TableConfig) -> None:
    if table_config.source.adapter in supported_change_event_adapter_names():
        return

    raise ValueError(
        "El adapter runtime "
        f"'{table_config.source.adapter}' no está soportado para la tabla '{table_name}'"
    )


def _ensure_table_sync_mode(table_name: str, table_config: TableConfig) -> None:
    if table_config.sync.mode in VALID_SYNC_MODES:
        return

    raise ValueError(
        f"El modo de sincronización '{table_config.sync.mode}' no está soportado "
        f"para la tabla '{table_name}'"
    )


def _build_clickhouse_config(raw_destination: object) -> ClickHouseConfig:
    destination_config = _expect_dict(
        raw_destination,
        "La configuración runtime.destination",
    )
    adapter = _expect_non_empty_str(
        _required_value(
            destination_config,
            "adapter",
            "La configuración runtime.destination",
        ),
        "La configuración runtime.destination.adapter",
    )
    if adapter != CLICKHOUSE_RUNTIME_ADAPTER:
        raise ValueError(
            "La configuración runtime.destination.adapter debe ser 'clickhouse'"
        )

    credentials_config = _expect_dict(
        _required_value(
            destination_config,
            "credentials",
            "La configuración runtime.destination",
        ),
        "La configuración runtime.destination.credentials",
    )

    return ClickHouseConfig(
        host=_expect_non_empty_str(
            _required_value(
                destination_config,
                "host",
                "La configuración runtime.destination",
            ),
            "La configuración runtime.destination.host",
        ),
        port=_expect_positive_int(
            _required_value(
                destination_config,
                "port",
                "La configuración runtime.destination",
            ),
            "La configuración runtime.destination.port",
        ),
        secure=_expect_bool(
            _required_value(
                destination_config,
                "secure",
                "La configuración runtime.destination",
            ),
            "La configuración runtime.destination.secure",
        ),
        database=_expect_non_empty_str(
            _required_value(
                destination_config,
                "database",
                "La configuración runtime.destination",
            ),
            "La configuración runtime.destination.database",
        ),
        user=_expect_non_empty_str(
            _required_value(
                credentials_config,
                "user",
                "La configuración runtime.destination.credentials",
            ),
            "La configuración runtime.destination.credentials.user",
        ),
        password=_expect_non_empty_str(
            _required_value(
                credentials_config,
                "password",
                "La configuración runtime.destination.credentials",
            ),
            "La configuración runtime.destination.credentials.password",
        ),
    )


def _build_kafka_topics(
    kafka_config: dict[object, object],
    tables: dict[str, TableConfig],
) -> list[str]:
    kafka_topics = [
        _expect_non_empty_str(
            topic,
            "La configuración runtime.kafka.topics[]",
        )
        for topic in _expect_list(
            _required_value(kafka_config, "topics", "La configuración runtime.kafka"),
            "La configuración runtime.kafka.topics",
        )
    ]
    if not kafka_topics:
        raise ValueError(
            "La configuración runtime.kafka.topics debe incluir al menos un topic"
        )

    table_topics = _build_table_topics(tables)
    if kafka_topics == table_topics:
        return kafka_topics

    raise ValueError(
        "La configuración runtime.kafka.topics debe coincidir con los topics "
        "derivados de las tablas habilitadas"
    )


def _build_table_topics(tables: dict[str, TableConfig]) -> list[str]:
    topics: list[str] = []
    seen_topics: set[str] = set()

    for table_config in tables.values():
        topic = table_config.source.topic
        if topic in seen_topics:
            raise ValueError(
                f"El topic '{topic}' está duplicado en la configuración runtime"
            )

        seen_topics.add(topic)
        topics.append(topic)

    return topics


def _warn_if_clickhouse_security_port_combo_is_suspicious(
    clickhouse: ClickHouseConfig,
) -> None:
    if clickhouse.secure and clickhouse.port == COMMON_INSECURE_CLICKHOUSE_PORT:
        warnings.warn(
            "El destino ClickHouse runtime usa secure=true con port=9000, una combinación no habitual. "
            "Para el entorno local usa 9000/false y para ClickHouse Cloud 9440/true.",
            UserWarning,
            stacklevel=2,
        )
        return

    if clickhouse.secure or clickhouse.port not in COMMON_SECURE_CLICKHOUSE_PORTS:
        return

    warnings.warn(
        f"El destino ClickHouse runtime usa port={clickhouse.port} con secure=false. "
        "Revisa la configuración si el destino es ClickHouse Cloud.",
        UserWarning,
        stacklevel=2,
    )


def _required_value(
    value: dict[object, object],
    key: str,
    label: str,
) -> object:
    try:
        return value[key]
    except KeyError as exc:
        raise ValueError(f"{label}.{key} es obligatorio") from exc


def _expect_dict(value: object, label: str) -> dict[object, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} debe ser un objeto JSON")

    return value


def _expect_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{label} debe ser una lista")

    return value


def _expect_non_empty_str(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} debe ser una cadena")

    normalized_value = value.strip()
    if normalized_value:
        return normalized_value

    raise ValueError(f"{label} no puede estar vacío")


def _expect_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{label} debe ser booleano")

    return value


def _expect_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{label} debe ser un entero")

    return value


def _expect_positive_int(value: object, label: str) -> int:
    parsed_value = _expect_int(value, label)
    if parsed_value > 0:
        return parsed_value

    raise ValueError(f"{label} debe ser mayor que 0")
