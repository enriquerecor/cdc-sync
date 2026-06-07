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

RUNTIME_WORKER_EXAMPLE = {
    "worker_id": "local-worker",
}
RUNTIME_KAFKA_EXAMPLE = {
    "bootstrap_servers": "kafka:29092",
    "client_id": "cdc-sync-worker-local-worker",
    "group_id": "cdc-sync-worker-local-worker",
    "auto_offset_reset": "earliest",
    "poll_timeout_ms": 1000,
    "topics": ["cdc_sync.public.customers"],
}
RUNTIME_DESTINATION_CREDENTIALS_EXAMPLE = {
    "user": "cdc_sync",
    "password": "cdc_sync",
}
RUNTIME_DESTINATION_EXAMPLE = {
    "adapter": "clickhouse",
    "host": "clickhouse",
    "port": 9000,
    "secure": False,
    "database": "cdc_sync_analytics",
    "credentials": RUNTIME_DESTINATION_CREDENTIALS_EXAMPLE,
}
RUNTIME_TABLE_SOURCE_EXAMPLE = {
    "adapter": "debezium_postgres",
    "schema": "public",
    "table": "customers",
    "topic": "cdc_sync.public.customers",
}
RUNTIME_TABLE_SYNC_EXAMPLE = {
    "mode": "realtime",
}
RUNTIME_DESTINATION_COLUMN_EXAMPLE = {
    "name": "id",
    "type": "UInt64",
    "nullable": False,
}
RUNTIME_TABLE_DESTINATION_EXAMPLE = {
    "table": "customers",
    "columns": [
        RUNTIME_DESTINATION_COLUMN_EXAMPLE,
        {
            "name": "email",
            "type": "String",
            "nullable": True,
        },
    ],
}
RUNTIME_TABLE_EXAMPLE = {
    "enabled": True,
    "source": RUNTIME_TABLE_SOURCE_EXAMPLE,
    "pk": ["id"],
    "sync": RUNTIME_TABLE_SYNC_EXAMPLE,
    "destination": RUNTIME_TABLE_DESTINATION_EXAMPLE,
}
WORKER_RUNTIME_CONFIG_EXAMPLE = {
    "contract_version": 1,
    "worker": RUNTIME_WORKER_EXAMPLE,
    "kafka": RUNTIME_KAFKA_EXAMPLE,
    "destination": RUNTIME_DESTINATION_EXAMPLE,
    "tables": {
        "customers": RUNTIME_TABLE_EXAMPLE,
    },
}


class RuntimeWorkerResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [RUNTIME_WORKER_EXAMPLE]},
    )

    worker_id: str

    @classmethod
    def from_dto(cls, dto: RuntimeWorkerDto) -> "RuntimeWorkerResponse":
        return cls(worker_id=dto.worker_id)


class RuntimeKafkaResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [RUNTIME_KAFKA_EXAMPLE]},
    )

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
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [RUNTIME_DESTINATION_CREDENTIALS_EXAMPLE]},
    )

    user: str
    password: str

    @classmethod
    def from_dto(
        cls,
        dto: RuntimeDestinationCredentialsDto,
    ) -> "RuntimeDestinationCredentialsResponse":
        return cls(user=dto.user, password=dto.password)


class RuntimeDestinationResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [RUNTIME_DESTINATION_EXAMPLE]},
    )

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
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [RUNTIME_TABLE_SOURCE_EXAMPLE]},
    )

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
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [RUNTIME_TABLE_SYNC_EXAMPLE]},
    )

    mode: str

    @classmethod
    def from_dto(cls, dto: RuntimeTableSyncDto) -> "RuntimeTableSyncResponse":
        return cls(mode=dto.mode)


class RuntimeDestinationColumnResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [RUNTIME_DESTINATION_COLUMN_EXAMPLE]},
    )

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
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [RUNTIME_TABLE_DESTINATION_EXAMPLE]},
    )

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
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [RUNTIME_TABLE_EXAMPLE]},
    )

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
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [WORKER_RUNTIME_CONFIG_EXAMPLE]},
    )

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
