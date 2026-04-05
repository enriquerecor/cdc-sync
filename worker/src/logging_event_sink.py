import logging
from dataclasses import dataclass

from event_sink import EventSink
from normalized_event import NormalizedEvent

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoggingEventSink(EventSink):
    client_id: str

    def persist(self, event: NormalizedEvent) -> None:
        LOGGER.info(
            "cdc_event client_id=%s table=%s operation=%s version=%s deleted=%s primary_key=%s data=%s",
            self.client_id,
            event.table,
            event.operation.value,
            event.version,
            event.deleted,
            event.primary_key,
            event.data,
        )
