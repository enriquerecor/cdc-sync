from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EditingSourceConnectionDto:
    name: str
    host: str
    port: int
    database: str
    username: str
    password: str


@dataclass(frozen=True)
class EditingDestinationColumnDto:
    name: str
    type: str
    nullable: bool | None


@dataclass(frozen=True)
class EditingTableDto:
    logical_name: str
    enabled: bool
    source_adapter: str
    source_connection: str
    source_schema: str | None
    source_table: str
    source_topic: str
    primary_key_fields: tuple[str, ...]
    sync_mode: str
    destination_table: str
    destination_default_nullable: bool | None
    destination_columns: tuple[EditingDestinationColumnDto, ...]


@dataclass(frozen=True)
class EditingConfigDto:
    version: int | None
    updated_at: datetime | None
    source_connections: tuple[EditingSourceConnectionDto, ...]
    tables: tuple[EditingTableDto, ...]


@dataclass(frozen=True)
class SaveEditingConfigDto:
    expected_version: int | None
    source_connections: tuple[EditingSourceConnectionDto, ...]
    tables: tuple[EditingTableDto, ...]
