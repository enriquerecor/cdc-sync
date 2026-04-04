import logging
from typing import Optional

from kafka import KafkaConsumer
from kafka.consumer.fetcher import ConsumerRecord

from config import WorkerConfig

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


def consume_forever(consumer: KafkaConsumer, config: WorkerConfig) -> None:
    try:
        while True:
            polled_records = consumer.poll(timeout_ms=config.kafka_poll_timeout_ms)
            _log_records(config, polled_records)
    finally:
        consumer.close()


def _log_records(
    config: WorkerConfig, polled_records: dict[object, list[ConsumerRecord]]
) -> None:
    for _, records in polled_records.items():
        for record in records:
            LOGGER.info(
                "cdc_event client_id=%s topic=%s partition=%s offset=%s key=%s value=%s",
                config.kafka_client_id,
                record.topic,
                record.partition,
                record.offset,
                record.key if record.key is not None else "null",
                record.value if record.value is not None else "null",
            )


def _deserialize_payload(payload: Optional[bytes]) -> Optional[str]:
    if payload is None:
        return None

    return payload.decode("utf-8", errors="replace")
