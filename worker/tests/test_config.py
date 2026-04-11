import pytest

from config import load_config


def test_load_config_includes_clickhouse_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKER_KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    monkeypatch.setenv("WORKER_KAFKA_CLIENT_ID", "cdc-sync-worker")
    monkeypatch.setenv("WORKER_KAFKA_GROUP_ID", "cdc-sync-worker")
    monkeypatch.setenv("WORKER_KAFKA_AUTO_OFFSET_RESET", "earliest")
    monkeypatch.setenv("WORKER_KAFKA_POLL_TIMEOUT_MS", "1000")
    monkeypatch.setenv(
        "WORKER_TABLE_CONFIG_PATH",
        "worker/config/tables.example.json",
    )
    monkeypatch.setenv("WORKER_CLICKHOUSE_HOST", "clickhouse")
    monkeypatch.setenv("WORKER_CLICKHOUSE_PORT", "9000")
    monkeypatch.setenv("WORKER_CLICKHOUSE_DB", "cdc_sync_analytics")
    monkeypatch.setenv("WORKER_CLICKHOUSE_USER", "cdc_sync")
    monkeypatch.setenv("WORKER_CLICKHOUSE_PASSWORD", "cdc_sync")

    config = load_config()

    assert config.clickhouse.host == "clickhouse"
    assert config.clickhouse.port == 9000
    assert config.clickhouse.database == "cdc_sync_analytics"
    assert config.clickhouse.user == "cdc_sync"
    assert config.clickhouse.password == "cdc_sync"
