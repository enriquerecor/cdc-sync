from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr

from cdc_sync_api.application.dto.editing_config_dto import (
    EditingConfigDto,
    EditingDestinationColumnDto,
    EditingSourceConnectionDto,
    EditingTableDto,
    SaveEditingConfigDto,
)


class EditingSourceConnectionBody(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )
    name: StrictStr = Field(min_length=1)
    host: StrictStr = Field(min_length=1)
    port: StrictInt = Field(gt=0)
    database: StrictStr = Field(min_length=1)
    username: StrictStr = Field(min_length=1)
    password: StrictStr = Field(min_length=1)

    def to_dto(self) -> EditingSourceConnectionDto:
        return EditingSourceConnectionDto(
            name=self.name,
            host=self.host,
            port=self.port,
            database=self.database,
            username=self.username,
            password=self.password,
        )

    @classmethod
    def from_dto(cls, dto: EditingSourceConnectionDto) -> "EditingSourceConnectionBody":
        return cls(
            name=dto.name,
            host=dto.host,
            port=dto.port,
            database=dto.database,
            username=dto.username,
            password=dto.password,
        )


class EditingDestinationColumnBody(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )
    name: StrictStr = Field(min_length=1)
    type: StrictStr = Field(min_length=1)
    nullable: StrictBool | None = None

    def to_dto(self) -> EditingDestinationColumnDto:
        return EditingDestinationColumnDto(
            name=self.name,
            type=self.type,
            nullable=self.nullable,
        )

    @classmethod
    def from_dto(cls, dto: EditingDestinationColumnDto) -> "EditingDestinationColumnBody":
        return cls(
            name=dto.name,
            type=dto.type,
            nullable=dto.nullable,
        )


class EditingTableSourceBody(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )
    adapter: StrictStr = Field(min_length=1)
    connection: StrictStr = Field(min_length=1)
    schema_name: StrictStr | None = Field(default=None, alias="schema", min_length=1)
    table: StrictStr = Field(min_length=1)
    topic: StrictStr = Field(min_length=1)


class EditingTableSyncBody(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )
    mode: StrictStr = Field(min_length=1)


class EditingTableDestinationBody(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )
    table: StrictStr = Field(min_length=1)
    default_nullable: StrictBool | None = None
    columns: list[EditingDestinationColumnBody]


class EditingTableBody(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )
    name: StrictStr = Field(min_length=1)
    enabled: StrictBool
    source: EditingTableSourceBody
    pk: list[StrictStr]
    sync: EditingTableSyncBody
    destination: EditingTableDestinationBody

    def to_dto(self) -> EditingTableDto:
        return EditingTableDto(
            logical_name=self.name,
            enabled=self.enabled,
            source_adapter=self.source.adapter,
            source_connection=self.source.connection,
            source_schema=self.source.schema_name,
            source_table=self.source.table,
            source_topic=self.source.topic,
            primary_key_fields=tuple(self.pk),
            sync_mode=self.sync.mode,
            destination_table=self.destination.table,
            destination_default_nullable=self.destination.default_nullable,
            destination_columns=tuple(
                column.to_dto() for column in self.destination.columns
            ),
        )

    @classmethod
    def from_dto(cls, dto: EditingTableDto) -> "EditingTableBody":
        return cls(
            name=dto.logical_name,
            enabled=dto.enabled,
            source=EditingTableSourceBody(
                adapter=dto.source_adapter,
                connection=dto.source_connection,
                schema=dto.source_schema,
                table=dto.source_table,
                topic=dto.source_topic,
            ),
            pk=list(dto.primary_key_fields),
            sync=EditingTableSyncBody(mode=dto.sync_mode),
            destination=EditingTableDestinationBody(
                table=dto.destination_table,
                default_nullable=dto.destination_default_nullable,
                columns=[
                    EditingDestinationColumnBody.from_dto(column)
                    for column in dto.destination_columns
                ],
            ),
        )


class PutEditingConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    expected_version: StrictInt | None = Field(default=None, gt=0)
    source_connections: list[EditingSourceConnectionBody]
    tables: list[EditingTableBody]

    def to_dto(self) -> SaveEditingConfigDto:
        return SaveEditingConfigDto(
            expected_version=self.expected_version,
            source_connections=tuple(
                source.to_dto() for source in self.source_connections
            ),
            tables=tuple(table.to_dto() for table in self.tables),
        )


class EditingConfigResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: StrictInt
    updated_at: datetime
    source_connections: list[EditingSourceConnectionBody]
    tables: list[EditingTableBody]

    @classmethod
    def from_dto(cls, dto: EditingConfigDto) -> "EditingConfigResponse":
        if dto.version is None or dto.updated_at is None:
            raise ValueError("EditingConfigResponse requiere version y updated_at")

        return cls(
            version=dto.version,
            updated_at=dto.updated_at,
            source_connections=[
                EditingSourceConnectionBody.from_dto(source)
                for source in dto.source_connections
            ],
            tables=[EditingTableBody.from_dto(table) for table in dto.tables],
        )
