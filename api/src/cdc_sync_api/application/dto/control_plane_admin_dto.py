from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CredentialsDto:
    user: str
    password: str


@dataclass(frozen=True)
class WorkerRequestDto:
    worker_id: str
    name: str
    description: str | None
    enabled: bool


@dataclass(frozen=True)
class SourceConnectionCreateDto:
    name: str
    source_type: str
    host: str
    port: int
    database_name: str
    credentials: CredentialsDto


@dataclass(frozen=True)
class SourceConnectionUpdateDto:
    name: str
    source_type: str
    host: str
    port: int
    database_name: str
    credentials: CredentialsDto | None


@dataclass(frozen=True)
class DestinationCreateDto:
    name: str
    destination_type: str
    host: str
    port: int
    secure: bool
    database_name: str
    credentials: CredentialsDto


@dataclass(frozen=True)
class DestinationUpdateDto:
    name: str
    destination_type: str
    host: str
    port: int
    secure: bool
    database_name: str
    credentials: CredentialsDto | None


@dataclass(frozen=True)
class DestinationColumnDto:
    name: str
    destination_type: str
    nullable: bool


@dataclass(frozen=True)
class ConfiguredTableDto:
    logical_name: str
    source_schema: str
    source_table: str
    cdc_topic: str
    destination_table: str
    primary_key_fields: tuple[str, ...]
    destination_columns: tuple[DestinationColumnDto, ...]
    enabled: bool


@dataclass(frozen=True)
class SyncConfigRequestDto:
    name: str
    source_connection_id: UUID
    destination_id: UUID
    sync_mode: str
    tables: tuple[ConfiguredTableDto, ...]
    enabled: bool


@dataclass(frozen=True)
class AssignmentRequestDto:
    config_id: UUID

