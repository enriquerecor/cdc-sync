from dataclasses import dataclass

import main as main_module
from config import ClickHouseConfig, WorkerConfig
from .helpers import build_table_config


@dataclass
class FakeConsumer:
    pass


@dataclass
class FakeRegistry:
    database: str
    tables: dict[str, object]


@dataclass
class FakeClickHouseClient:
    config: ClickHouseConfig
    database: str | None = None

    def execute(self, query: str) -> None:
        raise AssertionError("No deberia llamarse directamente en este test")

    def insert_rows(self, query: str, rows: list[dict[str, object]]) -> None:
        raise AssertionError("No deberia llamarse directamente en este test")


@dataclass
class FakeSchemaManager:
    database_executor: object
    table_executor: object
    table_registry: object
    bootstrap_called: bool = False

    def bootstrap(self) -> None:
        self.bootstrap_called = True


def test_main_wires_clickhouse_event_sink(monkeypatch) -> None:
    fake_config = WorkerConfig(
        worker_id="local-worker",
        control_plane_base_url="http://localhost:8000",
        runtime_contract_version=1,
        kafka_bootstrap_servers="kafka:29092",
        kafka_topics=["cdc_sync.public.customers"],
        kafka_client_id="cdc-sync-worker",
        kafka_group_id="cdc-sync-worker",
        kafka_auto_offset_reset="earliest",
        kafka_poll_timeout_ms=1000,
        tables={
            "customers": build_table_config(
                table="customers",
                topic="cdc_sync.public.customers",
                primary_key_fields=("id",),
                destination_columns=(
                    ("id", "UInt64", False),
                    ("email", "String", True),
                ),
            )
        },
        clickhouse=ClickHouseConfig(
            host="clickhouse",
            port=9000,
            secure=False,
            database="cdc_sync_analytics",
            user="cdc_sync",
            password="cdc_sync",
        ),
    )
    fake_parser = object()
    fake_consumer = FakeConsumer()
    fake_registry = FakeRegistry(
        database="cdc_sync_analytics",
        tables={"customers": object()},
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(main_module, "load_config", lambda: fake_config)
    monkeypatch.setattr(main_module.logging, "basicConfig", lambda **_: None)
    monkeypatch.setattr(
        main_module,
        "build_change_event_adapters",
        lambda: {"debezium_postgres": object()},
    )

    class FakeParserFactory:
        def __new__(cls, adapters, tables):
            captured["parser_adapters"] = adapters
            captured["parser_tables"] = tables
            return fake_parser

    monkeypatch.setattr(main_module, "NormalizedEventParser", FakeParserFactory)
    monkeypatch.setattr(main_module, "build_consumer", lambda config: fake_consumer)
    monkeypatch.setattr(
        main_module,
        "build_clickhouse_table_registry",
        lambda clickhouse_config, tables: fake_registry,
    )

    created_schema_managers: list[FakeSchemaManager] = []

    def fake_schema_manager_factory(
        database_executor: object,
        table_executor: object,
        table_registry: object,
    ) -> FakeSchemaManager:
        manager = FakeSchemaManager(
            database_executor=database_executor,
            table_executor=table_executor,
            table_registry=table_registry,
        )
        created_schema_managers.append(manager)
        return manager

    monkeypatch.setattr(main_module, "ClickHouseClient", FakeClickHouseClient)
    monkeypatch.setattr(main_module, "ClickHouseSchemaManager", fake_schema_manager_factory)

    def fake_consume_forever(consumer, config, event_parser, event_sink) -> None:
        captured["consumer"] = consumer
        captured["config"] = config
        captured["event_parser"] = event_parser
        captured["event_sink"] = event_sink

    monkeypatch.setattr(main_module, "consume_forever", fake_consume_forever)

    main_module.main()

    assert captured["consumer"] is fake_consumer
    assert captured["config"] is fake_config
    assert captured["event_parser"] is fake_parser
    assert isinstance(captured["event_sink"], main_module.ClickHouseEventSink)
    assert captured["event_sink"].table_registry is fake_registry
    assert isinstance(captured["event_sink"].row_writer, FakeClickHouseClient)
    assert captured["event_sink"].row_writer.database == "cdc_sync_analytics"
    assert len(created_schema_managers) == 1
    assert created_schema_managers[0].bootstrap_called is True
    assert created_schema_managers[0].table_registry is fake_registry
    assert isinstance(created_schema_managers[0].database_executor, FakeClickHouseClient)
    assert created_schema_managers[0].database_executor.database is None
    assert isinstance(created_schema_managers[0].table_executor, FakeClickHouseClient)
    assert created_schema_managers[0].table_executor.database == "cdc_sync_analytics"
