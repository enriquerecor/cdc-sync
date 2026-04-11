import json
import logging
from json import JSONDecodeError
from typing import Optional

from kafka import KafkaConsumer
from kafka.consumer.fetcher import ConsumerRecord

from config import WorkerConfig
from normalized_event import NormalizedEvent
from normalized_event_parser import NormalizedEventParser

LOGGER = logging.getLogger(__name__)


def build_consumer(config: WorkerConfig) -> KafkaConsumer:
    consumer = KafkaConsumer(
        bootstrap_servers=config.kafka_bootstrap_servers,
        client_id=config.kafka_client_id,
        group_id=config.kafka_group_id,
        auto_offset_reset=config.kafka_auto_offset_reset,
        enable_auto_commit=True,  # TODO: en el futuro será `False` para garantizar `at-least-once processing`
        key_deserializer=_deserialize_payload,
        value_deserializer=_deserialize_payload,
    )
    consumer.subscribe(topics=config.kafka_topics)

    return consumer


def consume_forever(
    consumer: KafkaConsumer,
    config: WorkerConfig,
    event_parser: NormalizedEventParser,
) -> None:
    try:
        while True:
            polled_records = consumer.poll(timeout_ms=config.kafka_poll_timeout_ms)
            _log_records(config, event_parser, polled_records)
    finally:
        consumer.close()


def _log_records(
    config: WorkerConfig,
    event_parser: NormalizedEventParser,
    polled_records: dict[object, list[ConsumerRecord]],
) -> None:
    for _, records in polled_records.items():
        for record in records:
            normalized_event = _parse_record(record, event_parser)
            if normalized_event is None:
                continue

            _log_normalized_event(config, record, normalized_event)


def _parse_record(
    record: ConsumerRecord,
    event_parser: NormalizedEventParser,
) -> NormalizedEvent | None:
    try:
        return event_parser.parse(record.topic, record.value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "No se pudo normalizar el evento "
            f"topic={record.topic} partition={record.partition} offset={record.offset}"
        ) from exc


def _log_normalized_event(
    config: WorkerConfig,
    record: ConsumerRecord,
    event: NormalizedEvent,
) -> None:
    LOGGER.info(
        "cdc_event client_id=%s topic=%s partition=%s offset=%s table=%s operation=%s version=%s source_position=%s deleted=%s primary_key=%s data=%s",
        config.kafka_client_id,
        record.topic,
        record.partition,
        record.offset,
        event.table,
        event.operation.value,
        event.version,
        event.source_position,
        event.deleted,
        event.primary_key,
        event.data,
    )


def _deserialize_payload(payload: Optional[bytes]) -> object | None:
    if payload is None:
        return None

    try:
        raw_payload = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("El payload de Kafka no es UTF-8 valido") from exc

    try:
        return json.loads(raw_payload)
    except JSONDecodeError as exc:
        raise ValueError("El payload de Kafka no es JSON valido") from exc
