import logging

import pytest

from logging_event_sink import LoggingEventSink
from normalized_event import NormalizedEvent, Operation


def test_logging_event_sink_logs_normalized_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sink = LoggingEventSink(client_id="cdc-sync-worker")
    event = NormalizedEvent(
        table="customers",
        primary_key={"id": 1},
        data={"id": 1, "email": "log-sink@example.com"},
        version=101,
        deleted=False,
        operation=Operation.INSERT,
    )

    with caplog.at_level(logging.INFO):
        sink.persist(event)

    assert len(caplog.messages) == 1
    assert "cdc_event client_id=cdc-sync-worker" in caplog.messages[0]
    assert "table=customers" in caplog.messages[0]
    assert "operation=insert" in caplog.messages[0]
    assert "primary_key={'id': 1}" in caplog.messages[0]
    assert "data={'id': 1, 'email': 'log-sink@example.com'}" in caplog.messages[0]
