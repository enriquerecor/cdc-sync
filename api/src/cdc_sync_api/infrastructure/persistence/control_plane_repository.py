from sqlalchemy.engine import Engine

from cdc_sync_api.infrastructure.persistence.control_plane_assignment_repository import (
    AssignmentPersistenceMixin,
)
from cdc_sync_api.infrastructure.persistence.control_plane_config_repository import (
    ConfigPersistenceMixin,
)
from cdc_sync_api.infrastructure.persistence.control_plane_connection_repository import (
    ConnectionPersistenceMixin,
)
from cdc_sync_api.infrastructure.persistence.control_plane_secret_repository import (
    SecretPersistenceMixin,
)
from cdc_sync_api.infrastructure.persistence.control_plane_worker_repository import (
    WorkerPersistenceMixin,
)


class SqlAlchemyControlPlaneRepository(
    WorkerPersistenceMixin,
    ConnectionPersistenceMixin,
    ConfigPersistenceMixin,
    AssignmentPersistenceMixin,
    SecretPersistenceMixin,
):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
