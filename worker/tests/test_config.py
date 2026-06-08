from copy import deepcopy

import pytest

from config import build_config_from_runtime, load_config


def test_load_config_builds_worker_config_from_remote_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_remote_worker_environment(monkeypatch)
    captured_request: dict[str, str] = {}

    def fetcher(control_plane_base_url: str, worker_id: str) -> dict[object, object]:
        captured_request["control_plane_base_url"] = control_plane_base_url
        captured_request["worker_id"] = worker_id
        return _runtime_config()

    config = load_config(fetcher)

    assert captured_request == {
        "control_plane_base_url": "http://localhost:8000",
        "worker_id": "local-worker",
    }
    assert config.worker_id == "local-worker"
    assert config.control_plane_base_url == "http://localhost:8000"
    assert config.runtime_contract_version == 1
    assert config.kafka_bootstrap_servers == "kafka:29092"
    assert config.kafka_topics == ["cdc_sync.public.customers"]
    assert config.kafka_client_id == "cdc-sync-worker-local-worker"
    assert config.kafka_group_id == "cdc-sync-worker-local-worker"
    assert config.kafka_auto_offset_reset == "earliest"
    assert config.kafka_poll_timeout_ms == 1000
    assert config.clickhouse.host == "clickhouse"
    assert config.clickhouse.port == 9000
    assert config.clickhouse.secure is False
    assert config.clickhouse.database == "cdc_sync_analytics"
    assert config.clickhouse.user == "cdc_sync"
    assert config.clickhouse.password == "cdc_sync"
    assert tuple(config.tables) == ("customers",)
    assert config.tables["customers"].source.adapter == "debezium_postgres"
    assert config.tables["customers"].source.schema == "public"
    assert not hasattr(config.tables["customers"].source, "connection")


def test_load_config_fails_without_worker_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_remote_worker_environment(monkeypatch)
    monkeypatch.delenv("WORKER_ID")

    with pytest.raises(ValueError, match="La variable WORKER_ID es obligatoria"):
        load_config(lambda *_: _runtime_config())


def test_load_config_fails_without_control_plane_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_remote_worker_environment(monkeypatch)
    monkeypatch.delenv("WORKER_CONTROL_PLANE_BASE_URL")

    with pytest.raises(
        ValueError,
        match="La variable WORKER_CONTROL_PLANE_BASE_URL es obligatoria",
    ):
        load_config(lambda *_: _runtime_config())


def test_load_config_fails_with_invalid_control_plane_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_remote_worker_environment(monkeypatch)
    monkeypatch.setenv("WORKER_CONTROL_PLANE_BASE_URL", "api:8000")

    with pytest.raises(
        ValueError,
        match="La variable WORKER_CONTROL_PLANE_BASE_URL debe ser una URL con esquema y host",
    ):
        load_config(lambda *_: _runtime_config())


def test_build_config_fails_when_runtime_worker_does_not_match() -> None:
    runtime_config = _runtime_config()
    runtime_config["worker"]["worker_id"] = "another-worker"

    with pytest.raises(
        ValueError,
        match="pertenece al worker 'another-worker'",
    ):
        _build_config(runtime_config)


def test_build_config_fails_with_unsupported_contract_version() -> None:
    runtime_config = _runtime_config()
    runtime_config["contract_version"] = 2

    with pytest.raises(ValueError, match="versión de contrato no soportada"):
        _build_config(runtime_config)


def test_build_config_fails_without_destination_credentials() -> None:
    runtime_config = _runtime_config()
    runtime_config["destination"]["credentials"] = {"user": "cdc_sync"}

    with pytest.raises(
        ValueError,
        match="La configuración runtime.destination.credentials.password es obligatorio",
    ):
        _build_config(runtime_config)


def test_build_config_fails_when_kafka_topics_do_not_match_tables() -> None:
    runtime_config = _runtime_config()
    runtime_config["kafka"]["topics"] = ["cdc_sync.public.orders"]

    with pytest.raises(
        ValueError,
        match="debe coincidir con los topics derivados",
    ):
        _build_config(runtime_config)


def test_build_config_fails_with_invalid_auto_offset_reset() -> None:
    runtime_config = _runtime_config()
    runtime_config["kafka"]["auto_offset_reset"] = "middle"

    with pytest.raises(
        ValueError,
        match="auto_offset_reset debe ser 'earliest' o 'latest'",
    ):
        _build_config(runtime_config)


def test_build_config_fails_with_unsupported_destination_adapter() -> None:
    runtime_config = _runtime_config()
    runtime_config["destination"]["adapter"] = "postgresql"

    with pytest.raises(
        ValueError,
        match="destination.adapter debe ser 'clickhouse'",
    ):
        _build_config(runtime_config)


def test_build_config_fails_with_unsupported_table_adapter() -> None:
    runtime_config = _runtime_config()
    runtime_config["tables"]["customers"]["source"]["adapter"] = "unsupported"

    with pytest.raises(
        ValueError,
        match="no está soportado para la tabla 'customers'",
    ):
        _build_config(runtime_config)


def test_build_config_fails_with_unsupported_sync_mode() -> None:
    runtime_config = _runtime_config()
    runtime_config["tables"]["customers"]["sync"]["mode"] = "batch"

    with pytest.raises(
        ValueError,
        match="El modo de sincronización 'batch' no está soportado",
    ):
        _build_config(runtime_config)


def _set_remote_worker_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_ID", "local-worker")
    monkeypatch.setenv("WORKER_CONTROL_PLANE_BASE_URL", "http://localhost:8000")


def _build_config(runtime_config: dict[str, object]):
    return build_config_from_runtime(
        worker_id="local-worker",
        control_plane_base_url="http://localhost:8000",
        runtime_config=runtime_config,
    )


def _runtime_config() -> dict[str, object]:
    return deepcopy(
        {
            "contract_version": 1,
            "worker": {"worker_id": "local-worker"},
            "kafka": {
                "bootstrap_servers": "kafka:29092",
                "client_id": "cdc-sync-worker-local-worker",
                "group_id": "cdc-sync-worker-local-worker",
                "auto_offset_reset": "earliest",
                "poll_timeout_ms": 1000,
                "topics": ["cdc_sync.public.customers"],
            },
            "destination": {
                "adapter": "clickhouse",
                "host": "clickhouse",
                "port": 9000,
                "secure": False,
                "database": "cdc_sync_analytics",
                "credentials": {
                    "user": "cdc_sync",
                    "password": "cdc_sync",
                },
            },
            "tables": {
                "customers": {
                    "enabled": True,
                    "source": {
                        "adapter": "debezium_postgres",
                        "schema": "public",
                        "table": "customers",
                        "topic": "cdc_sync.public.customers",
                    },
                    "pk": ["id"],
                    "sync": {"mode": "realtime"},
                    "destination": {
                        "table": "customers",
                        "columns": [
                            {"name": "id", "type": "UInt64", "nullable": False},
                            {"name": "email", "type": "String", "nullable": True},
                        ],
                    },
                }
            },
        }
    )
