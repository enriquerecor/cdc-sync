from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class WorkerConfigAssignmentDto:
    worker_internal_id: UUID
    worker_id: str
    config_id: UUID
    assigned_at: datetime
