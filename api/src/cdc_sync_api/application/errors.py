class ControlPlaneConflictError(RuntimeError):
    """La operación administrativa entra en conflicto con el estado persistido."""


class ControlPlaneNotFoundError(RuntimeError):
    """La entidad administrativa solicitada no existe."""
