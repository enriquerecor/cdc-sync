import logging

from config import load_config
from consumer import build_consumer, consume_forever


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("kafka").setLevel(logging.WARNING)

    config = load_config()
    logging.info(
        "worker_started bootstrap_servers=%s topic_pattern=%s client_id=%s group_id=%s",
        config.kafka_bootstrap_servers,
        config.kafka_topic_pattern,
        config.kafka_client_id,
        config.kafka_group_id,
    )

    consumer = build_consumer(config)

    try:
        consume_forever(consumer, config)
    except KeyboardInterrupt:
        logging.info("worker_stopped")


if __name__ == "__main__":
    main()
