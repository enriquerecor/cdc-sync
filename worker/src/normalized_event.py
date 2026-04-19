from dataclasses import dataclass
from enum import Enum

from normalized_value import NormalizedRow


class Operation(Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    SNAPSHOT = "snapshot"


@dataclass(frozen=True)
class NormalizedEvent:
    table: str
    primary_key: NormalizedRow
    data: NormalizedRow
    version: int
    source_position: dict[str, object]
    deleted: bool
    operation: Operation
