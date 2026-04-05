from typing import Protocol

from normalized_event import Operation


class ChangeEventAdapter(Protocol):
    def is_tombstone(self, value: object) -> bool:
        """Return whether the source event is a tombstone and should be ignored."""

    def extract_table_name(self, topic: str, value: dict[str, object]) -> str:
        """Return the logical table name without schema information."""

    def extract_operation(self, value: dict[str, object]) -> Operation:
        """Map the source event operation to the internal normalized contract."""

    def extract_data(
        self, value: dict[str, object], operation: Operation
    ) -> dict[str, object]:
        """Extract the row snapshot that corresponds to the normalized operation."""

    def extract_version(self, value: dict[str, object]) -> int:
        """Resolve a comparable version value for the normalized event."""

    def extract_source_position(self, value: dict[str, object]) -> dict[str, object]:
        """Expose source-specific position metadata for tracing and future adapters."""
