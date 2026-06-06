from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
from uuid import UUID

from cdc_sync_api.domain.control_plane import (
    SecretReference,
    SourceConnection,
    SourceType,
    SyncConfig,
)


@dataclass(frozen=True)
class CdcConnectorCompileRequest:
    source_connection: SourceConnection
    credentials: SecretReference
    configs: tuple[SyncConfig, ...]


@dataclass(frozen=True)
class CompiledCdcConnector:
    connector_name: str
    source_connection_id: UUID
    source_type: SourceType
    connector_class: str
    topic_prefix: str
    captured_tables: tuple[str, ...]
    config: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "captured_tables", tuple(self.captured_tables))
        object.__setattr__(self, "config", MappingProxyType(dict(self.config)))


@dataclass(frozen=True)
class MaterializedCdcConnectorDto:
    connector_name: str
    source_connection_id: UUID
    source_type: str
    connector_class: str
    topic_prefix: str
    captured_tables: tuple[str, ...]

    @classmethod
    def from_compiled(
        cls,
        compiled_connector: CompiledCdcConnector,
    ) -> "MaterializedCdcConnectorDto":
        return cls(
            connector_name=compiled_connector.connector_name,
            source_connection_id=compiled_connector.source_connection_id,
            source_type=compiled_connector.source_type.value,
            connector_class=compiled_connector.connector_class,
            topic_prefix=compiled_connector.topic_prefix,
            captured_tables=compiled_connector.captured_tables,
        )
