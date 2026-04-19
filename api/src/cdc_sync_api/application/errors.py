class EditingConfigNotFoundError(RuntimeError):
    """La configuración en edición no existe."""


class EditingConfigConflictError(RuntimeError):
    """La configuración en edición cambió durante la operación."""
