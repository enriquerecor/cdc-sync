import clickhouse_client as clickhouse_client_module
from clickhouse_client import ClickHouseClient
from config import ClickHouseConfig


def test_clickhouse_client_enables_tls_when_config_is_secure(monkeypatch) -> None:
    captured_client_kwargs: dict[str, object] = {}

    class FakeDriverClient:
        def __init__(self, **kwargs) -> None:
            captured_client_kwargs.update(kwargs)

        def execute(self, query: str, rows=None) -> None:
            assert query == "SELECT 1"
            assert rows is None

    monkeypatch.setattr(clickhouse_client_module, "Client", FakeDriverClient)

    client = ClickHouseClient(
        ClickHouseConfig(
            host="cluster.clickhouse.cloud",
            port=9440,
            secure=True,
            database="analytics",
            user="default",
            password="secret",
        ),
        database="analytics",
    )

    client.execute("SELECT 1")

    assert captured_client_kwargs == {
        "host": "cluster.clickhouse.cloud",
        "port": 9440,
        "secure": True,
        "database": "analytics",
        "user": "default",
        "password": "secret",
    }
