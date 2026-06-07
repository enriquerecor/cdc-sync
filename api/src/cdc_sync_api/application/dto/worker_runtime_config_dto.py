from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeWorkerDto:
    worker_id: str


@dataclass(frozen=True)
class RuntimeKafkaDto:
    bootstrap_servers: str
    client_id: str
    group_id: str
    auto_offset_reset: str
    poll_timeout_ms: int
    topics: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeDestinationCredentialsDto:
    user: str
    password: str


@dataclass(frozen=True)
class RuntimeDestinationDto:
    adapter: str
    host: str
    port: int
    secure: bool
    database: str
    credentials: RuntimeDestinationCredentialsDto


@dataclass(frozen=True)
class RuntimeTableSourceDto:
    adapter: str
    schema: str
    table: str
    topic: str


@dataclass(frozen=True)
class RuntimeTableSyncDto:
    mode: str


@dataclass(frozen=True)
class RuntimeDestinationColumnDto:
    name: str
    type: str
    nullable: bool


@dataclass(frozen=True)
class RuntimeTableDestinationDto:
    table: str
    columns: tuple[RuntimeDestinationColumnDto, ...]


@dataclass(frozen=True)
class RuntimeTableDto:
    enabled: bool
    source: RuntimeTableSourceDto
    pk: tuple[str, ...]
    sync: RuntimeTableSyncDto
    destination: RuntimeTableDestinationDto


@dataclass(frozen=True)
class WorkerRuntimeConfigDto:
    contract_version: int
    worker: RuntimeWorkerDto
    kafka: RuntimeKafkaDto
    destination: RuntimeDestinationDto
    tables: dict[str, RuntimeTableDto]
