from __future__ import annotations

from typing import Mapping
from urllib.parse import quote

import httpx

from cdc_sync_api.application.errors import KafkaConnectRequestError


class HttpKafkaConnectClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        normalized_base_url = base_url.strip().rstrip("/")
        if normalized_base_url:
            self._base_url = normalized_base_url
            self._timeout_seconds = timeout_seconds
            return

        raise ValueError("base_url de Kafka Connect no puede estar vacío")

    def put_connector_config(
        self,
        connector_name: str,
        config: Mapping[str, str],
    ) -> None:
        try:
            response = httpx.put(
                self._connector_config_url(connector_name),
                json=dict(config),
                timeout=self._timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise KafkaConnectRequestError(
                f"No se pudo contactar con Kafka Connect para materializar "
                f"el conector '{connector_name}'"
            ) from exc

        if response.is_success:
            return

        raise KafkaConnectRequestError(
            f"Kafka Connect rechazó la configuración del conector "
            f"'{connector_name}' con estado {response.status_code}"
        )

    def _connector_config_url(self, connector_name: str) -> str:
        encoded_connector_name = quote(connector_name, safe="")
        return f"{self._base_url}/connectors/{encoded_connector_name}/config"
