from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from cdc_sync_api.application.dto.cdc_connector_dto import (
    MaterializedCdcConnectorDto,
)
from cdc_sync_api.application.dto.control_plane_admin_dto import (
    AssignmentRequestDto,
    ConfiguredTableDto,
    CredentialsDto,
    DestinationColumnDto,
    DestinationCreateDto,
    DestinationUpdateDto,
    SourceConnectionCreateDto,
    SourceConnectionUpdateDto,
    SyncConfigRequestDto,
    WorkerRequestDto,
)
from cdc_sync_api.application.dto.control_plane_assignment_dto import (
    WorkerConfigAssignmentDto,
)
from cdc_sync_api.domain.control_plane import (
    ConfiguredTable,
    Destination,
    DestinationColumn,
    SourceConnection,
    SyncConfig,
    Worker,
)

NonEmptyStr = Annotated[str, Field(strict=True, min_length=1)]
Port = Annotated[int, Field(strict=True, ge=1, le=65535)]
StrictBool = Annotated[bool, Field(strict=True)]

WORKER_INTERNAL_ID_EXAMPLE = "11111111-1111-4111-8111-111111111111"
SOURCE_CONNECTION_ID_EXAMPLE = "22222222-2222-4222-8222-222222222222"
DESTINATION_ID_EXAMPLE = "33333333-3333-4333-8333-333333333333"
CONFIG_ID_EXAMPLE = "44444444-4444-4444-8444-444444444444"

CREDENTIALS_EXAMPLE = {
    "user": "cdc_sync",
    "password": "cdc_sync",
}
WORKER_REQUEST_EXAMPLE = {
    "worker_id": "local-worker",
    "name": "Worker local",
    "description": "Worker de la demo local",
    "kafka_group_id": None,
    "enabled": True,
}
WORKER_RESPONSE_EXAMPLE = {
    "id": WORKER_INTERNAL_ID_EXAMPLE,
    **WORKER_REQUEST_EXAMPLE,
}
SOURCE_CONNECTION_CREATE_EXAMPLE = {
    "name": "PostgreSQL local",
    "source_type": "postgresql",
    "host": "postgres",
    "port": 5432,
    "database_name": "cdc_sync",
    "credentials": CREDENTIALS_EXAMPLE,
}
SOURCE_CONNECTION_RESPONSE_EXAMPLE = {
    "id": SOURCE_CONNECTION_ID_EXAMPLE,
    "name": "PostgreSQL local",
    "source_type": "postgresql",
    "host": "postgres",
    "port": 5432,
    "database_name": "cdc_sync",
    "credentials_configured": True,
}
DESTINATION_CREATE_EXAMPLE = {
    "name": "ClickHouse local",
    "destination_type": "clickhouse",
    "host": "clickhouse",
    "port": 9000,
    "secure": False,
    "database_name": "cdc_sync_analytics",
    "credentials": CREDENTIALS_EXAMPLE,
}
DESTINATION_RESPONSE_EXAMPLE = {
    "id": DESTINATION_ID_EXAMPLE,
    "name": "ClickHouse local",
    "destination_type": "clickhouse",
    "host": "clickhouse",
    "port": 9000,
    "secure": False,
    "database_name": "cdc_sync_analytics",
    "credentials_configured": True,
}
DESTINATION_COLUMN_EXAMPLE = {
    "name": "id",
    "destination_type": "UInt64",
    "nullable": False,
}
CONFIGURED_TABLE_EXAMPLE = {
    "logical_name": "customers",
    "source_schema": "public",
    "source_table": "customers",
    "cdc_topic": "cdc_sync.public.customers",
    "destination_table": "customers",
    "primary_key_fields": ["id"],
    "destination_columns": [
        DESTINATION_COLUMN_EXAMPLE,
        {
            "name": "email",
            "destination_type": "String",
            "nullable": True,
        },
    ],
    "enabled": True,
}
SYNC_CONFIG_REQUEST_EXAMPLE = {
    "name": "Configuración local",
    "source_connection_id": SOURCE_CONNECTION_ID_EXAMPLE,
    "destination_id": DESTINATION_ID_EXAMPLE,
    "sync_mode": "realtime",
    "tables": [CONFIGURED_TABLE_EXAMPLE],
    "enabled": True,
}
SYNC_CONFIG_RESPONSE_EXAMPLE = {
    "id": CONFIG_ID_EXAMPLE,
    **SYNC_CONFIG_REQUEST_EXAMPLE,
}
ASSIGNMENT_REQUEST_EXAMPLE = {
    "config_id": CONFIG_ID_EXAMPLE,
}
ASSIGNMENT_RESPONSE_EXAMPLE = {
    "worker_internal_id": WORKER_INTERNAL_ID_EXAMPLE,
    "worker_id": "local-worker",
    "config_id": CONFIG_ID_EXAMPLE,
    "assigned_at": "2026-06-07T10:00:00Z",
}
CDC_CONNECTOR_MATERIALIZATION_EXAMPLE = {
    "connector_name": (
        f"cdc-sync-postgresql-{SOURCE_CONNECTION_ID_EXAMPLE}"
    ),
    "source_connection_id": SOURCE_CONNECTION_ID_EXAMPLE,
    "source_type": "postgresql",
    "connector_class": "io.debezium.connector.postgresql.PostgresConnector",
    "topic_prefix": "cdc_sync",
    "captured_tables": ["public.customers"],
}


class CredentialsRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={"examples": [CREDENTIALS_EXAMPLE]},
    )

    user: NonEmptyStr
    password: NonEmptyStr

    def to_dto(self) -> CredentialsDto:
        return CredentialsDto(user=self.user, password=self.password)


class WorkerRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={"examples": [WORKER_REQUEST_EXAMPLE]},
    )

    worker_id: NonEmptyStr
    name: NonEmptyStr
    description: str | None = None
    kafka_group_id: NonEmptyStr | None = None
    enabled: StrictBool = True

    def to_dto(self) -> WorkerRequestDto:
        return WorkerRequestDto(
            worker_id=self.worker_id,
            name=self.name,
            description=self.description,
            kafka_group_id=self.kafka_group_id,
            enabled=self.enabled,
        )


class WorkerResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [WORKER_RESPONSE_EXAMPLE]},
    )

    id: UUID
    worker_id: str
    name: str
    description: str | None
    kafka_group_id: str | None
    enabled: bool

    @classmethod
    def from_domain(cls, worker: Worker) -> "WorkerResponse":
        return cls(
            id=worker.id,
            worker_id=worker.worker_id,
            name=worker.name,
            description=worker.description,
            kafka_group_id=worker.kafka_group_id,
            enabled=worker.enabled,
        )


class SourceConnectionCreateRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={"examples": [SOURCE_CONNECTION_CREATE_EXAMPLE]},
    )

    name: NonEmptyStr
    source_type: NonEmptyStr = "postgresql"
    host: NonEmptyStr
    port: Port
    database_name: NonEmptyStr
    credentials: CredentialsRequest

    def to_dto(self) -> SourceConnectionCreateDto:
        return SourceConnectionCreateDto(
            name=self.name,
            source_type=self.source_type,
            host=self.host,
            port=self.port,
            database_name=self.database_name,
            credentials=self.credentials.to_dto(),
        )


class SourceConnectionUpdateRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "PostgreSQL local",
                    "source_type": "postgresql",
                    "host": "postgres",
                    "port": 5432,
                    "database_name": "cdc_sync",
                }
            ]
        },
    )

    name: NonEmptyStr
    source_type: NonEmptyStr = "postgresql"
    host: NonEmptyStr
    port: Port
    database_name: NonEmptyStr
    credentials: CredentialsRequest | None = None

    def to_dto(self) -> SourceConnectionUpdateDto:
        return SourceConnectionUpdateDto(
            name=self.name,
            source_type=self.source_type,
            host=self.host,
            port=self.port,
            database_name=self.database_name,
            credentials=(
                None if self.credentials is None else self.credentials.to_dto()
            ),
        )


class SourceConnectionResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [SOURCE_CONNECTION_RESPONSE_EXAMPLE]},
    )

    id: UUID
    name: str
    source_type: str
    host: str
    port: int
    database_name: str
    credentials_configured: bool

    @classmethod
    def from_domain(
        cls,
        source_connection: SourceConnection,
    ) -> "SourceConnectionResponse":
        return cls(
            id=source_connection.id,
            name=source_connection.name,
            source_type=source_connection.source_type.value,
            host=source_connection.host,
            port=source_connection.port,
            database_name=source_connection.database_name,
            credentials_configured=True,
        )


class CdcConnectorMaterializationResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [CDC_CONNECTOR_MATERIALIZATION_EXAMPLE]},
    )

    connector_name: str
    source_connection_id: UUID
    source_type: str
    connector_class: str
    topic_prefix: str
    captured_tables: tuple[str, ...]

    @classmethod
    def from_dto(
        cls,
        dto: MaterializedCdcConnectorDto,
    ) -> "CdcConnectorMaterializationResponse":
        return cls(
            connector_name=dto.connector_name,
            source_connection_id=dto.source_connection_id,
            source_type=dto.source_type,
            connector_class=dto.connector_class,
            topic_prefix=dto.topic_prefix,
            captured_tables=dto.captured_tables,
        )


class DestinationCreateRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={"examples": [DESTINATION_CREATE_EXAMPLE]},
    )

    name: NonEmptyStr
    destination_type: NonEmptyStr = "clickhouse"
    host: NonEmptyStr
    port: Port
    secure: StrictBool = False
    database_name: NonEmptyStr
    credentials: CredentialsRequest

    def to_dto(self) -> DestinationCreateDto:
        return DestinationCreateDto(
            name=self.name,
            destination_type=self.destination_type,
            host=self.host,
            port=self.port,
            secure=self.secure,
            database_name=self.database_name,
            credentials=self.credentials.to_dto(),
        )


class DestinationUpdateRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "ClickHouse local",
                    "destination_type": "clickhouse",
                    "host": "clickhouse",
                    "port": 9000,
                    "secure": False,
                    "database_name": "cdc_sync_analytics",
                }
            ]
        },
    )

    name: NonEmptyStr
    destination_type: NonEmptyStr = "clickhouse"
    host: NonEmptyStr
    port: Port
    secure: StrictBool = False
    database_name: NonEmptyStr
    credentials: CredentialsRequest | None = None

    def to_dto(self) -> DestinationUpdateDto:
        return DestinationUpdateDto(
            name=self.name,
            destination_type=self.destination_type,
            host=self.host,
            port=self.port,
            secure=self.secure,
            database_name=self.database_name,
            credentials=(
                None if self.credentials is None else self.credentials.to_dto()
            ),
        )


class DestinationResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [DESTINATION_RESPONSE_EXAMPLE]},
    )

    id: UUID
    name: str
    destination_type: str
    host: str
    port: int
    secure: bool
    database_name: str
    credentials_configured: bool

    @classmethod
    def from_domain(cls, destination: Destination) -> "DestinationResponse":
        return cls(
            id=destination.id,
            name=destination.name,
            destination_type=destination.destination_type.value,
            host=destination.host,
            port=destination.port,
            secure=destination.secure,
            database_name=destination.database_name,
            credentials_configured=True,
        )


class DestinationColumnRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={"examples": [DESTINATION_COLUMN_EXAMPLE]},
    )

    name: NonEmptyStr
    destination_type: NonEmptyStr
    nullable: StrictBool

    def to_dto(self) -> DestinationColumnDto:
        return DestinationColumnDto(
            name=self.name,
            destination_type=self.destination_type,
            nullable=self.nullable,
        )


class DestinationColumnResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [DESTINATION_COLUMN_EXAMPLE]},
    )

    name: str
    destination_type: str
    nullable: bool

    @classmethod
    def from_domain(
        cls,
        destination_column: DestinationColumn,
    ) -> "DestinationColumnResponse":
        return cls(
            name=destination_column.name,
            destination_type=destination_column.destination_type,
            nullable=destination_column.nullable,
        )


class ConfiguredTableRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={"examples": [CONFIGURED_TABLE_EXAMPLE]},
    )

    logical_name: NonEmptyStr
    source_schema: NonEmptyStr
    source_table: NonEmptyStr
    cdc_topic: NonEmptyStr
    destination_table: NonEmptyStr
    primary_key_fields: tuple[NonEmptyStr, ...] = Field(min_length=1)
    destination_columns: tuple[DestinationColumnRequest, ...] = Field(min_length=1)
    enabled: StrictBool = True

    def to_dto(self) -> ConfiguredTableDto:
        return ConfiguredTableDto(
            logical_name=self.logical_name,
            source_schema=self.source_schema,
            source_table=self.source_table,
            cdc_topic=self.cdc_topic,
            destination_table=self.destination_table,
            primary_key_fields=self.primary_key_fields,
            destination_columns=tuple(
                column.to_dto() for column in self.destination_columns
            ),
            enabled=self.enabled,
        )


class ConfiguredTableResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [CONFIGURED_TABLE_EXAMPLE]},
    )

    logical_name: str
    source_schema: str
    source_table: str
    cdc_topic: str
    destination_table: str
    primary_key_fields: tuple[str, ...]
    destination_columns: tuple[DestinationColumnResponse, ...]
    enabled: bool

    @classmethod
    def from_domain(cls, table: ConfiguredTable) -> "ConfiguredTableResponse":
        return cls(
            logical_name=table.logical_name,
            source_schema=table.source_schema,
            source_table=table.source_table,
            cdc_topic=table.cdc_topic,
            destination_table=table.destination_table,
            primary_key_fields=table.primary_key_fields,
            destination_columns=tuple(
                DestinationColumnResponse.from_domain(column)
                for column in table.destination_columns
            ),
            enabled=table.enabled,
        )


class SyncConfigRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={"examples": [SYNC_CONFIG_REQUEST_EXAMPLE]},
    )

    name: NonEmptyStr
    source_connection_id: UUID
    destination_id: UUID
    sync_mode: NonEmptyStr = "realtime"
    tables: tuple[ConfiguredTableRequest, ...] = Field(min_length=1)
    enabled: StrictBool = True

    def to_dto(self) -> SyncConfigRequestDto:
        return SyncConfigRequestDto(
            name=self.name,
            source_connection_id=self.source_connection_id,
            destination_id=self.destination_id,
            sync_mode=self.sync_mode,
            tables=tuple(table.to_dto() for table in self.tables),
            enabled=self.enabled,
        )


class SyncConfigResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [SYNC_CONFIG_RESPONSE_EXAMPLE]},
    )

    id: UUID
    name: str
    source_connection_id: UUID
    destination_id: UUID
    sync_mode: str
    tables: tuple[ConfiguredTableResponse, ...]
    enabled: bool

    @classmethod
    def from_domain(cls, config: SyncConfig) -> "SyncConfigResponse":
        return cls(
            id=config.id,
            name=config.name,
            source_connection_id=config.source_connection_id,
            destination_id=config.destination_id,
            sync_mode=config.sync_mode.value,
            tables=tuple(
                ConfiguredTableResponse.from_domain(table)
                for table in config.tables
            ),
            enabled=config.enabled,
        )


class AssignmentRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={"examples": [ASSIGNMENT_REQUEST_EXAMPLE]},
    )

    config_id: UUID

    def to_dto(self) -> AssignmentRequestDto:
        return AssignmentRequestDto(config_id=self.config_id)


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [ASSIGNMENT_RESPONSE_EXAMPLE]},
    )

    worker_internal_id: UUID
    worker_id: str
    config_id: UUID
    assigned_at: datetime

    @classmethod
    def from_dto(cls, dto: WorkerConfigAssignmentDto) -> "AssignmentResponse":
        return cls(
            worker_internal_id=dto.worker_internal_id,
            worker_id=dto.worker_id,
            config_id=dto.config_id,
            assigned_at=dto.assigned_at,
        )
