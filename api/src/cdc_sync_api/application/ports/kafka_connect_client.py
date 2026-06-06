from typing import Mapping, Protocol


class KafkaConnectClient(Protocol):
    def put_connector_config(
        self,
        connector_name: str,
        config: Mapping[str, str],
    ) -> None:
        """Crea o actualiza de forma idempotente la config de un conector."""
