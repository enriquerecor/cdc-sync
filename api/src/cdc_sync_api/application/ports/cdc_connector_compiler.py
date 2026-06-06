from typing import Protocol

from cdc_sync_api.application.dto.cdc_connector_dto import (
    CdcConnectorCompileRequest,
    CompiledCdcConnector,
)
from cdc_sync_api.domain.control_plane import SourceType


class CdcConnectorCompiler(Protocol):
    @property
    def source_type(self) -> SourceType:
        """Tipo de origen CDC soportado por el compilador."""

    def compile(
        self,
        request: CdcConnectorCompileRequest,
    ) -> CompiledCdcConnector:
        """Compila la configuración idempotente de un conector CDC."""
