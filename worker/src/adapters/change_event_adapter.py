from typing import Protocol

from normalized_event import Operation


class ChangeEventAdapter(Protocol):
    def extract_table_name(self, topic: str, value: dict[str, object]) -> str:
        """Return the logical table name without schema information."""

    def extract_operation(self, value: dict[str, object]) -> Operation:
        """Map the source event operation to the internal normalized contract."""

    def extract_data(
        self, value: dict[str, object], operation: Operation
    ) -> dict[str, object]:
        """Extract the row snapshot that corresponds to the normalized operation."""
