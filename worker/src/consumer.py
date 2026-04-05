import json
from json import JSONDecodeError
from typing import Optional

from kafka import KafkaConsumer
from kafka.consumer.fetcher import ConsumerRecord

from config import WorkerConfig
from event_sink import EventSink
from normalized_event import NormalizedEvent
from normalized_event_parser import NormalizedEventParser


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
    event_sink: EventSink,
) -> None:
    try:
        while True:
            polled_records = consumer.poll(timeout_ms=config.kafka_poll_timeout_ms)
            _persist_records(config, event_parser, event_sink, polled_records)
    finally:
        consumer.close()


def _persist_records(
    config: WorkerConfig,
    event_parser: NormalizedEventParser,
    event_sink: EventSink,
    polled_records: dict[object, list[ConsumerRecord]],
) -> None:
    for _, records in polled_records.items():
        for record in records:
            normalized_event = _parse_record(record, event_parser)
            if normalized_event is None:
                continue

            _persist_event(config, record, normalized_event, event_sink)


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


def _persist_event(
    config: WorkerConfig,
    record: ConsumerRecord,
    event: NormalizedEvent,
    event_sink: EventSink,
) -> None:
    try:
        event_sink.persist(event)
    except Exception as exc:
        raise RuntimeError(
            "No se pudo persistir el evento normalizado "
            f"client_id={config.kafka_client_id} topic={record.topic} "
            f"partition={record.partition} offset={record.offset} "
            f"table={event.table} operation={event.operation.value} "
            f"version={event.version} source_position={event.source_position}"
        ) from exc


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
