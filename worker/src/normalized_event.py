from dataclasses import dataclass
from enum import Enum


class Operation(Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    SNAPSHOT = "snapshot"


@dataclass(frozen=True)
class NormalizedEvent:
    table: str
    primary_key: dict[str, object]
    data: dict[str, object]
    version: int
    source_position: dict[str, object]
    deleted: bool
    operation: Operation
