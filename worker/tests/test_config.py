import pytest

from config import load_config


def _set_minimal_worker_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_ID", "local-worker")
    monkeypatch.setenv("WORKER_CONTROL_PLANE_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("WORKER_KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    monkeypatch.setenv("WORKER_KAFKA_CLIENT_ID", "cdc-sync-worker")
    monkeypatch.setenv("WORKER_KAFKA_GROUP_ID", "cdc-sync-worker")
    monkeypatch.setenv("WORKER_KAFKA_AUTO_OFFSET_RESET", "earliest")
    monkeypatch.setenv("WORKER_KAFKA_POLL_TIMEOUT_MS", "1000")
    monkeypatch.setenv(
        "WORKER_TABLE_CONFIG_PATH",
        "worker/config/tables.example.json",
    )


def test_load_config_includes_worker_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_minimal_worker_environment(monkeypatch)

    config = load_config()

    assert config.worker_id == "local-worker"
    assert config.control_plane_base_url == "http://localhost:8000"


def test_load_config_fails_without_worker_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_minimal_worker_environment(monkeypatch)
    monkeypatch.delenv("WORKER_ID")

    with pytest.raises(ValueError, match="La variable WORKER_ID es obligatoria"):
        load_config()


def test_load_config_fails_without_control_plane_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_worker_environment(monkeypatch)
    monkeypatch.delenv("WORKER_CONTROL_PLANE_BASE_URL")

    with pytest.raises(
        ValueError,
        match="La variable WORKER_CONTROL_PLANE_BASE_URL es obligatoria",
    ):
        load_config()


def test_load_config_fails_with_invalid_control_plane_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_worker_environment(monkeypatch)
    monkeypatch.setenv("WORKER_CONTROL_PLANE_BASE_URL", "api:8000")

    with pytest.raises(
        ValueError,
        match="La variable WORKER_CONTROL_PLANE_BASE_URL debe ser una URL con esquema y host",
    ):
        load_config()


def test_load_config_includes_clickhouse_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_minimal_worker_environment(monkeypatch)
    monkeypatch.setenv("WORKER_CLICKHOUSE_HOST", "clickhouse")
    monkeypatch.setenv("WORKER_CLICKHOUSE_PORT", "9000")
    monkeypatch.setenv("WORKER_CLICKHOUSE_SECURE", "false")
    monkeypatch.setenv("WORKER_CLICKHOUSE_DB", "cdc_sync_analytics")
    monkeypatch.setenv("WORKER_CLICKHOUSE_USER", "cdc_sync")
    monkeypatch.setenv("WORKER_CLICKHOUSE_PASSWORD", "cdc_sync")

    config = load_config()

    assert config.clickhouse.host == "clickhouse"
    assert config.clickhouse.port == 9000
    assert config.clickhouse.secure is False
    assert config.clickhouse.database == "cdc_sync_analytics"
    assert config.clickhouse.user == "cdc_sync"
    assert config.clickhouse.password == "cdc_sync"


def test_load_config_includes_explicit_secure_clickhouse_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_worker_environment(monkeypatch)
    monkeypatch.setenv("WORKER_CLICKHOUSE_PORT", "9440")
    monkeypatch.setenv("WORKER_CLICKHOUSE_SECURE", "true")

    config = load_config()

    assert config.clickhouse.port == 9440
    assert config.clickhouse.secure is True


def test_load_config_uses_insecure_clickhouse_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_worker_environment(monkeypatch)

    config = load_config()

    assert config.clickhouse.port == 9000
    assert config.clickhouse.secure is False


def test_load_config_warns_when_secure_clickhouse_uses_common_insecure_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_worker_environment(monkeypatch)
    monkeypatch.setenv("WORKER_CLICKHOUSE_PORT", "9000")
    monkeypatch.setenv("WORKER_CLICKHOUSE_SECURE", "true")

    with pytest.warns(
        UserWarning,
        match="WORKER_CLICKHOUSE_SECURE=true con WORKER_CLICKHOUSE_PORT=9000",
    ):
        load_config()


def test_load_config_warns_when_secure_clickhouse_port_disables_tls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_minimal_worker_environment(monkeypatch)
    monkeypatch.setenv("WORKER_CLICKHOUSE_PORT", "9440")
    monkeypatch.setenv("WORKER_CLICKHOUSE_SECURE", "false")

    with pytest.warns(
        UserWarning,
        match="WORKER_CLICKHOUSE_PORT=9440 suele requerir WORKER_CLICKHOUSE_SECURE=true",
    ):
        load_config()
