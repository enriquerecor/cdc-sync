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
