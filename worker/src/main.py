import logging

from adapters.registry import build_change_event_adapters
from config import load_config
from consumer import build_consumer, consume_forever
from logging_event_sink import LoggingEventSink
from normalized_event_parser import NormalizedEventParser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("kafka").setLevel(logging.WARNING)

    config = load_config()
    logging.info(
        "worker_started bootstrap_servers=%s topics=%s client_id=%s group_id=%s table_config_version=%s tables=%s table_config_path=%s",
        config.kafka_bootstrap_servers,
        ",".join(config.kafka_topics),
        config.kafka_client_id,
        config.kafka_group_id,
        config.table_config_version,
        ",".join(sorted(config.tables)),
        config.table_config_path,
    )

    event_parser = NormalizedEventParser(
        adapters=build_change_event_adapters(),
        tables=config.tables,
    )
    event_sink = LoggingEventSink(client_id=config.kafka_client_id)
    consumer = build_consumer(config)

    try:
        consume_forever(consumer, config, event_parser, event_sink)
    except KeyboardInterrupt:
        logging.info("worker_stopped")


if __name__ == "__main__":
    main()
