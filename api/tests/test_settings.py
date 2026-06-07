import pytest
from pydantic import ValidationError

from cdc_sync_api.shared.settings import Settings


def test_settings_does_not_load_fixed_env_file() -> None:
    assert Settings.model_config.get("env_file") is None


def test_settings_reads_kafka_connect_base_url_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("API_KAFKA_CONNECT_BASE_URL", "http://connect:8083")

    settings = Settings()

    assert settings.kafka_connect_base_url == "http://connect:8083"


def test_settings_uses_local_kafka_connect_base_url_by_default(monkeypatch) -> None:
    monkeypatch.delenv("API_KAFKA_CONNECT_BASE_URL", raising=False)

    settings = Settings()

    assert settings.kafka_connect_base_url == "http://localhost:8083"


def test_settings_reads_worker_kafka_runtime_settings(monkeypatch) -> None:
    monkeypatch.setenv("API_WORKER_KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    monkeypatch.setenv("API_WORKER_KAFKA_CLIENT_ID_PREFIX", "custom-worker")
    monkeypatch.setenv("API_WORKER_KAFKA_AUTO_OFFSET_RESET", "latest")
    monkeypatch.setenv("API_WORKER_KAFKA_POLL_TIMEOUT_MS", "2500")

    settings = Settings()

    assert settings.worker_kafka_bootstrap_servers == "kafka:29092"
    assert settings.worker_kafka_client_id_prefix == "custom-worker"
    assert settings.worker_kafka_auto_offset_reset == "latest"
    assert settings.worker_kafka_poll_timeout_ms == 2500


def test_settings_uses_worker_kafka_runtime_defaults(monkeypatch) -> None:
    monkeypatch.delenv("API_WORKER_KAFKA_BOOTSTRAP_SERVERS", raising=False)
    monkeypatch.delenv("API_WORKER_KAFKA_CLIENT_ID_PREFIX", raising=False)
    monkeypatch.delenv("API_WORKER_KAFKA_AUTO_OFFSET_RESET", raising=False)
    monkeypatch.delenv("API_WORKER_KAFKA_POLL_TIMEOUT_MS", raising=False)

    settings = Settings()

    assert settings.worker_kafka_bootstrap_servers == "localhost:9092"
    assert settings.worker_kafka_client_id_prefix == "cdc-sync-worker"
    assert settings.worker_kafka_auto_offset_reset == "earliest"
    assert settings.worker_kafka_poll_timeout_ms == 1000


@pytest.mark.parametrize(
    ("env_name", "env_value"),
    [
        ("API_WORKER_KAFKA_BOOTSTRAP_SERVERS", "   "),
        ("API_WORKER_KAFKA_CLIENT_ID_PREFIX", "   "),
        ("API_WORKER_KAFKA_AUTO_OFFSET_RESET", "middle"),
        ("API_WORKER_KAFKA_POLL_TIMEOUT_MS", "0"),
    ],
)
def test_settings_rejects_invalid_worker_kafka_runtime_values(
    monkeypatch,
    env_name: str,
    env_value: str,
) -> None:
    monkeypatch.setenv(env_name, env_value)

    with pytest.raises(ValidationError):
        Settings()
