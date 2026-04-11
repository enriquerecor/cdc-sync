class EventPersistenceError(RuntimeError):
    """Raised when a normalized event cannot be persisted in the configured sink."""


class OffsetCommitError(RuntimeError):
    """Raised when processed Kafka offsets cannot be committed."""
