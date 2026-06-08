from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from cdc_sync_api.application.dto.worker_runtime_config_dto import (
    RuntimeDestinationColumnDto,
    RuntimeDestinationCredentialsDto,
    RuntimeDestinationDto,
    RuntimeKafkaDto,
    RuntimeTableDestinationDto,
    RuntimeTableDto,
    RuntimeTableSourceDto,
    RuntimeTableSyncDto,
    RuntimeWorkerDto,
    WorkerRuntimeConfigDto,
)


class RuntimeWorkerResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    worker_id: str

    @classmethod
    def from_dto(cls, dto: RuntimeWorkerDto) -> "RuntimeWorkerResponse":
        return cls(worker_id=dto.worker_id)


class RuntimeKafkaResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    bootstrap_servers: str
    client_id: str
    group_id: str
    auto_offset_reset: str
    poll_timeout_ms: int
    topics: tuple[str, ...]

    @classmethod
    def from_dto(cls, dto: RuntimeKafkaDto) -> "RuntimeKafkaResponse":
        return cls(
            bootstrap_servers=dto.bootstrap_servers,
            client_id=dto.client_id,
            group_id=dto.group_id,
            auto_offset_reset=dto.auto_offset_reset,
            poll_timeout_ms=dto.poll_timeout_ms,
            topics=dto.topics,
        )


class RuntimeDestinationCredentialsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: str
    password: str

    @classmethod
    def from_dto(
        cls,
        dto: RuntimeDestinationCredentialsDto,
    ) -> "RuntimeDestinationCredentialsResponse":
        return cls(user=dto.user, password=dto.password)


class RuntimeDestinationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    adapter: str
    host: str
    port: int
    secure: bool
    database: str
    credentials: RuntimeDestinationCredentialsResponse

    @classmethod
    def from_dto(cls, dto: RuntimeDestinationDto) -> "RuntimeDestinationResponse":
        return cls(
            adapter=dto.adapter,
            host=dto.host,
            port=dto.port,
            secure=dto.secure,
            database=dto.database,
            credentials=RuntimeDestinationCredentialsResponse.from_dto(
                dto.credentials
            ),
        )


class RuntimeTableSourceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    adapter: str
    source_schema: str = Field(serialization_alias="schema")
    table: str
    topic: str

    @classmethod
    def from_dto(cls, dto: RuntimeTableSourceDto) -> "RuntimeTableSourceResponse":
        return cls(
            adapter=dto.adapter,
            source_schema=dto.schema,
            table=dto.table,
            topic=dto.topic,
        )


class RuntimeTableSyncResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: str

    @classmethod
    def from_dto(cls, dto: RuntimeTableSyncDto) -> "RuntimeTableSyncResponse":
        return cls(mode=dto.mode)


class RuntimeDestinationColumnResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    type: str
    nullable: bool

    @classmethod
    def from_dto(
        cls,
        dto: RuntimeDestinationColumnDto,
    ) -> "RuntimeDestinationColumnResponse":
        return cls(
            name=dto.name,
            type=dto.type,
            nullable=dto.nullable,
        )


class RuntimeTableDestinationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    table: str
    columns: tuple[RuntimeDestinationColumnResponse, ...]

    @classmethod
    def from_dto(
        cls,
        dto: RuntimeTableDestinationDto,
    ) -> "RuntimeTableDestinationResponse":
        return cls(
            table=dto.table,
            columns=tuple(
                RuntimeDestinationColumnResponse.from_dto(column)
                for column in dto.columns
            ),
        )


class RuntimeTableResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    source: RuntimeTableSourceResponse
    pk: tuple[str, ...]
    sync: RuntimeTableSyncResponse
    destination: RuntimeTableDestinationResponse

    @classmethod
    def from_dto(cls, dto: RuntimeTableDto) -> "RuntimeTableResponse":
        return cls(
            enabled=dto.enabled,
            source=RuntimeTableSourceResponse.from_dto(dto.source),
            pk=dto.pk,
            sync=RuntimeTableSyncResponse.from_dto(dto.sync),
            destination=RuntimeTableDestinationResponse.from_dto(dto.destination),
        )


class WorkerRuntimeConfigResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_version: int
    worker: RuntimeWorkerResponse
    kafka: RuntimeKafkaResponse
    destination: RuntimeDestinationResponse
    tables: dict[str, RuntimeTableResponse]

    @classmethod
    def from_dto(cls, dto: WorkerRuntimeConfigDto) -> "WorkerRuntimeConfigResponse":
        return cls(
            contract_version=dto.contract_version,
            worker=RuntimeWorkerResponse.from_dto(dto.worker),
            kafka=RuntimeKafkaResponse.from_dto(dto.kafka),
            destination=RuntimeDestinationResponse.from_dto(dto.destination),
            tables={
                logical_name: RuntimeTableResponse.from_dto(table)
                for logical_name, table in dto.tables.items()
            },
        )
