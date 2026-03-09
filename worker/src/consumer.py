import logging
from typing import Optional

from kafka import KafkaConsumer
from kafka.consumer.fetcher import ConsumerRecord

from config import WorkerConfig

LOGGER = logging.getLogger(__name__)


def build_consumer(config: WorkerConfig) -> KafkaConsumer:
    consumer = KafkaConsumer(
        bootstrap_servers=config.kafka_bootstrap_servers,
        group_id=config.kafka_group_id,
        auto_offset_reset=config.kafka_auto_offset_reset,
        enable_auto_commit=True,
    )
    consumer.subscribe(pattern=config.kafka_topic_pattern)
    return consumer


def consume_forever(consumer: KafkaConsumer, config: WorkerConfig) -> None:
    try:
        while True:
            polled_records = consumer.poll(timeout_ms=config.kafka_poll_timeout_ms)
            _log_records(polled_records)
    finally:
        consumer.close()


def _log_records(polled_records: dict[object, list[ConsumerRecord]]) -> None:
    for _, records in polled_records.items():
        for record in records:
            LOGGER.info(
                "cdc_event topic=%s partition=%s offset=%s key=%s value=%s",
                record.topic,
                record.partition,
                record.offset,
                _decode_payload(record.key),
                _decode_payload(record.value),
            )


def _decode_payload(payload: Optional[bytes]) -> str:
    if payload is None:
        return "null"
    return payload.decode("utf-8", errors="replace")
