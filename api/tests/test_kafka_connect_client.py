from __future__ import annotations

import httpx
import pytest

from cdc_sync_api.application.errors import KafkaConnectRequestError
from cdc_sync_api.infrastructure.kafka_connect.http_kafka_connect_client import (
    HttpKafkaConnectClient,
)


def test_http_kafka_connect_client_puts_connector_config(monkeypatch) -> None:
    captured_request: dict[str, object] = {}

    def fake_put(
        url: str,
        *,
        json: dict[str, str],
        timeout: float,
    ) -> httpx.Response:
        captured_request["url"] = url
        captured_request["json"] = json
        captured_request["timeout"] = timeout
        return httpx.Response(200)

    monkeypatch.setattr(
        "cdc_sync_api.infrastructure.kafka_connect.http_kafka_connect_client.httpx.put",
        fake_put,
    )

    HttpKafkaConnectClient("http://connect:8083/").put_connector_config(
        "cdc-sync-postgresql-source",
        {"connector.class": "example.Connector"},
    )

    assert captured_request == {
        "url": "http://connect:8083/connectors/cdc-sync-postgresql-source/config",
        "json": {"connector.class": "example.Connector"},
        "timeout": 10.0,
    }


def test_http_kafka_connect_client_raises_sanitized_error(monkeypatch) -> None:
    def fake_put(
        url: str,
        *,
        json: dict[str, str],
        timeout: float,
    ) -> httpx.Response:
        return httpx.Response(400)

    monkeypatch.setattr(
        "cdc_sync_api.infrastructure.kafka_connect.http_kafka_connect_client.httpx.put",
        fake_put,
    )

    with pytest.raises(KafkaConnectRequestError) as exc_info:
        HttpKafkaConnectClient("http://connect:8083").put_connector_config(
            "cdc-sync-postgresql-source",
            {
                "database.user": "cdc_sync",
                "database.password": "secret",
            },
        )

    assert "400" in str(exc_info.value)
    assert "secret" not in str(exc_info.value)
