import logging

from adapters.registry import build_change_event_adapters
from clickhouse_client import ClickHouseClient
from clickhouse_event_sink import ClickHouseEventSink
from clickhouse_schema_manager import ClickHouseSchemaManager
from clickhouse_table_registry import build_clickhouse_table_registry
from config import WorkerConfig, load_config
from consumer import build_consumer, consume_forever
from normalized_event_parser import NormalizedEventParser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("kafka").setLevel(logging.WARNING)

    config = load_config()
    logging.info(
        "worker_started worker_id=%s control_plane_base_url=%s bootstrap_servers=%s topics=%s client_id=%s group_id=%s table_config_version=%s tables=%s local_table_fixture_path=%s",
        config.worker_id,
        config.control_plane_base_url,
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
    event_sink = _build_event_sink(config)
    consumer = build_consumer(config)

    try:
        consume_forever(consumer, config, event_parser, event_sink)
    except KeyboardInterrupt:
        logging.info("worker_stopped")


def _build_event_sink(config: WorkerConfig) -> ClickHouseEventSink:
    clickhouse_table_registry = build_clickhouse_table_registry(
        config.clickhouse,
        config.tables,
    )
    clickhouse_schema_manager = ClickHouseSchemaManager(
        database_executor=ClickHouseClient(config.clickhouse),
        table_executor=ClickHouseClient(
            config.clickhouse,
            database=config.clickhouse.database,
        ),
        table_registry=clickhouse_table_registry,
    )
    clickhouse_schema_manager.bootstrap()
    logging.info(
        "clickhouse_schema_ready database=%s tables=%s",
        clickhouse_table_registry.database,
        ",".join(sorted(clickhouse_table_registry.tables)),
    )

    return ClickHouseEventSink(
        row_writer=ClickHouseClient(
            config.clickhouse,
            database=config.clickhouse.database,
        ),
        table_registry=clickhouse_table_registry,
    )


if __name__ == "__main__":
    main()
