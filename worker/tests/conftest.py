import pytest

from adapters.registry import build_change_event_adapters
from normalized_event_parser import NormalizedEventParser

from .helpers import build_table_config


@pytest.fixture
def parser() -> NormalizedEventParser:
    return NormalizedEventParser(
        adapters=build_change_event_adapters(),
        tables={
            "customers": build_table_config(
                table="customers",
                topic="cdc_sync.public.customers",
                primary_key_fields=("id",),
            ),
            "orders": build_table_config(
                table="orders",
                topic="cdc_sync.public.orders",
                primary_key_fields=("id",),
            ),
        },
    )
