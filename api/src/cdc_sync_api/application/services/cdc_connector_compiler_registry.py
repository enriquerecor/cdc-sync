from collections.abc import Iterable

from cdc_sync_api.application.ports.cdc_connector_compiler import (
    CdcConnectorCompiler,
)
from cdc_sync_api.domain.control_plane import (
    ControlPlaneValidationError,
    SourceType,
)


class CdcConnectorCompilerRegistry:
    def __init__(self, compilers: Iterable[CdcConnectorCompiler]) -> None:
        self._compilers_by_source_type = _index_compilers(compilers)

    def get(self, source_type: SourceType) -> CdcConnectorCompiler:
        compiler = self._compilers_by_source_type.get(source_type)
        if compiler is not None:
            return compiler

        raise ControlPlaneValidationError(
            f"No existe compilador CDC para source_type '{source_type.value}'"
        )


def _index_compilers(
    compilers: Iterable[CdcConnectorCompiler],
) -> dict[SourceType, CdcConnectorCompiler]:
    compilers_by_source_type: dict[SourceType, CdcConnectorCompiler] = {}

    for compiler in compilers:
        if compiler.source_type in compilers_by_source_type:
            raise ControlPlaneValidationError(
                f"El compilador CDC para '{compiler.source_type.value}' está duplicado"
            )

        compilers_by_source_type[compiler.source_type] = compiler

    return compilers_by_source_type
