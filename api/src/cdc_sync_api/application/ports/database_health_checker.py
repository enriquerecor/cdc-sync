from typing import Protocol


class DependencyUnavailableError(RuntimeError):
    """Error de infraestructura propagado como fallo explícito del caso de uso."""


class DatabaseHealthChecker(Protocol):
    def ensure_available(self) -> None:
        """Valida que la base de datos esté disponible."""
