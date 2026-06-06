class ControlPlaneConflictError(RuntimeError):
    """La operación administrativa entra en conflicto con el estado persistido."""


class ControlPlaneNotFoundError(RuntimeError):
    """La entidad administrativa solicitada no existe."""


class KafkaConnectRequestError(RuntimeError):
    """Kafka Connect no ha podido materializar la configuración indicada."""
