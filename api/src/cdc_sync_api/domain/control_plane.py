from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping, TypeVar
from uuid import UUID


TECHNICAL_DESTINATION_COLUMNS = frozenset({"version", "deleted"})


class ControlPlaneValidationError(ValueError):
    """Error explícito ante un modelo administrativo incompatible."""


class SecretProvider(StrEnum):
    INLINE = "inline"


class SourceType(StrEnum):
    POSTGRESQL = "postgresql"


class DestinationType(StrEnum):
    CLICKHOUSE = "clickhouse"


class SyncMode(StrEnum):
    REALTIME = "realtime"


EnumValue = TypeVar(
    "EnumValue",
    SecretProvider,
    SourceType,
    DestinationType,
    SyncMode,
)


@dataclass(frozen=True)
class SecretReference:
    id: UUID
    name: str
    provider: SecretProvider
    inline_payload: Mapping[str, str] | None = None
    external_reference: str | None = None

    def __post_init__(self) -> None:
        _ensure_uuid(self.id, "El id del secreto")
        object.__setattr__(self, "name", _ensure_non_empty_text(self.name, "name"))
        object.__setattr__(
            self,
            "provider",
            _coerce_enum(self.provider, SecretProvider, "provider"),
        )
        object.__setattr__(
            self,
            "external_reference",
            _normalize_optional_text(self.external_reference, "external_reference"),
        )

        if self.provider is not SecretProvider.INLINE:
            raise ControlPlaneValidationError(
                "El MVP solo soporta secretos con provider 'inline'"
            )

        if not self.inline_payload:
            raise ControlPlaneValidationError(
                "Los secretos inline deben incluir inline_payload"
            )

        normalized_payload = _normalize_secret_payload(self.inline_payload)
        object.__setattr__(
            self,
            "inline_payload",
            MappingProxyType(normalized_payload),
        )


@dataclass(frozen=True)
class Worker:
    id: UUID
    worker_id: str
    name: str
    description: str | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        _ensure_uuid(self.id, "El id interno del worker")
        object.__setattr__(
            self,
            "worker_id",
            _ensure_non_empty_text(self.worker_id, "worker_id"),
        )
        object.__setattr__(self, "name", _ensure_non_empty_text(self.name, "name"))
        object.__setattr__(
            self,
            "description",
            _normalize_optional_text(self.description, "description"),
        )
        _ensure_bool(self.enabled, "enabled")


@dataclass(frozen=True)
class SourceConnection:
    id: UUID
    name: str
    source_type: SourceType
    host: str
    port: int
    database_name: str
    credentials_secret_id: UUID

    def __post_init__(self) -> None:
        _ensure_uuid(self.id, "El id de la conexión de origen")
        _ensure_uuid(self.credentials_secret_id, "credentials_secret_id")
        object.__setattr__(self, "name", _ensure_non_empty_text(self.name, "name"))
        object.__setattr__(
            self,
            "source_type",
            _coerce_enum(self.source_type, SourceType, "source_type"),
        )
        object.__setattr__(self, "host", _ensure_non_empty_text(self.host, "host"))
        object.__setattr__(
            self,
            "database_name",
            _ensure_non_empty_text(self.database_name, "database_name"),
        )
        _ensure_port(self.port, "port")

        if self.source_type is not SourceType.POSTGRESQL:
            raise ControlPlaneValidationError(
                "El MVP solo soporta PostgreSQL como origen"
            )


@dataclass(frozen=True)
class Destination:
    id: UUID
    name: str
    destination_type: DestinationType
    host: str
    port: int
    secure: bool
    database_name: str
    credentials_secret_id: UUID

    def __post_init__(self) -> None:
        _ensure_uuid(self.id, "El id del destino")
        _ensure_uuid(self.credentials_secret_id, "credentials_secret_id")
        object.__setattr__(self, "name", _ensure_non_empty_text(self.name, "name"))
        object.__setattr__(
            self,
            "destination_type",
            _coerce_enum(self.destination_type, DestinationType, "destination_type"),
        )
        object.__setattr__(self, "host", _ensure_non_empty_text(self.host, "host"))
        object.__setattr__(
            self,
            "database_name",
            _ensure_non_empty_text(self.database_name, "database_name"),
        )
        _ensure_port(self.port, "port")
        _ensure_bool(self.secure, "secure")

        if self.destination_type is not DestinationType.CLICKHOUSE:
            raise ControlPlaneValidationError(
                "El MVP solo soporta ClickHouse como destino"
            )


@dataclass(frozen=True)
class DestinationColumn:
    name: str
    destination_type: str
    nullable: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _ensure_non_empty_text(self.name, "name"))
        object.__setattr__(
            self,
            "destination_type",
            _ensure_non_empty_text(self.destination_type, "destination_type"),
        )
        _ensure_bool(self.nullable, "nullable")

        if self.name in TECHNICAL_DESTINATION_COLUMNS:
            raise ControlPlaneValidationError(
                f"La columna técnica '{self.name}' no puede declararse en destino"
            )


@dataclass(frozen=True)
class ConfiguredTable:
    id: UUID
    logical_name: str
    source_schema: str
    source_table: str
    cdc_topic: str
    destination_table: str
    primary_key_fields: tuple[str, ...]
    destination_columns: tuple[DestinationColumn, ...]
    enabled: bool = True

    def __post_init__(self) -> None:
        _ensure_uuid(self.id, "El id de la tabla configurada")
        object.__setattr__(
            self,
            "logical_name",
            _ensure_non_empty_text(self.logical_name, "logical_name"),
        )
        object.__setattr__(
            self,
            "source_schema",
            _ensure_non_empty_text(self.source_schema, "source_schema"),
        )
        object.__setattr__(
            self,
            "source_table",
            _ensure_non_empty_text(self.source_table, "source_table"),
        )
        object.__setattr__(
            self,
            "cdc_topic",
            _ensure_non_empty_text(self.cdc_topic, "cdc_topic"),
        )
        object.__setattr__(
            self,
            "destination_table",
            _ensure_non_empty_text(self.destination_table, "destination_table"),
        )
        object.__setattr__(
            self,
            "primary_key_fields",
            _normalize_text_tuple(self.primary_key_fields, "primary_key_fields"),
        )
        object.__setattr__(
            self,
            "destination_columns",
            tuple(self.destination_columns),
        )
        _ensure_bool(self.enabled, "enabled")
        _validate_configured_table(self)


@dataclass(frozen=True)
class SyncConfig:
    id: UUID
    name: str
    source_connection_id: UUID
    destination_id: UUID
    sync_mode: SyncMode
    tables: tuple[ConfiguredTable, ...]
    enabled: bool = True

    def __post_init__(self) -> None:
        _ensure_uuid(self.id, "El id de la configuración")
        _ensure_uuid(self.source_connection_id, "source_connection_id")
        _ensure_uuid(self.destination_id, "destination_id")
        object.__setattr__(self, "name", _ensure_non_empty_text(self.name, "name"))
        object.__setattr__(
            self,
            "sync_mode",
            _coerce_enum(self.sync_mode, SyncMode, "sync_mode"),
        )
        object.__setattr__(self, "tables", tuple(self.tables))
        _ensure_bool(self.enabled, "enabled")

        if self.sync_mode is not SyncMode.REALTIME:
            raise ControlPlaneValidationError(
                "El MVP solo soporta sincronización realtime"
            )

        _validate_sync_config(self)


@dataclass(frozen=True)
class WorkerConfigAssignment:
    worker_id: UUID
    config_id: UUID
    assigned_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _ensure_uuid(self.worker_id, "worker_id")
        _ensure_uuid(self.config_id, "config_id")

        if self.assigned_at.tzinfo is None:
            raise ControlPlaneValidationError("assigned_at debe incluir zona horaria")


def _validate_configured_table(table: ConfiguredTable) -> None:
    if not table.primary_key_fields:
        raise ControlPlaneValidationError(
            f"La tabla '{table.logical_name}' debe declarar al menos una PK"
        )

    if not table.destination_columns:
        raise ControlPlaneValidationError(
            f"La tabla '{table.logical_name}' debe declarar columnas de destino"
        )

    destination_columns_by_name: dict[str, DestinationColumn] = {}
    for column in table.destination_columns:
        if column.name in destination_columns_by_name:
            raise ControlPlaneValidationError(
                f"La tabla '{table.logical_name}' declara la columna duplicada '{column.name}'"
            )

        destination_columns_by_name[column.name] = column

    for primary_key_field in table.primary_key_fields:
        column = destination_columns_by_name.get(primary_key_field)
        if column is None:
            raise ControlPlaneValidationError(
                f"La tabla '{table.logical_name}' debe incluir la PK '{primary_key_field}' en destino"
            )

        if column.nullable:
            raise ControlPlaneValidationError(
                f"La tabla '{table.logical_name}' marca la PK '{primary_key_field}' como nullable"
            )


def _validate_sync_config(config: SyncConfig) -> None:
    if not config.tables:
        raise ControlPlaneValidationError(
            "La configuración debe incluir al menos una tabla"
        )

    _ensure_unique_by(config.tables, "logical_name", "nombre lógico")
    _ensure_unique_by(config.tables, "cdc_topic", "topic CDC")
    _ensure_unique_by(config.tables, "destination_table", "tabla de destino")


def _ensure_unique_by(
    tables: tuple[ConfiguredTable, ...],
    attribute_name: str,
    label: str,
) -> None:
    seen_values: dict[str, str] = {}

    for table in tables:
        value = getattr(table, attribute_name)
        conflicting_table = seen_values.get(value)
        if conflicting_table is not None:
            raise ControlPlaneValidationError(
                f"El {label} '{value}' está duplicado para "
                f"'{conflicting_table}' y '{table.logical_name}'"
            )

        seen_values[value] = table.logical_name


def _ensure_uuid(value: UUID, label: str) -> None:
    if not isinstance(value, UUID):
        raise TypeError(f"{label} debe ser UUID")


def _ensure_non_empty_text(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} debe ser texto")

    normalized_value = value.strip()
    if not normalized_value:
        raise ControlPlaneValidationError(f"{label} no puede estar vacío")

    return normalized_value


def _normalize_optional_text(value: str | None, label: str) -> str | None:
    if value is None:
        return None

    normalized_value = _ensure_non_empty_text(value, label)
    return normalized_value


def _ensure_bool(value: bool, label: str) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{label} debe ser booleano")


def _ensure_port(value: int, label: str) -> None:
    if not isinstance(value, int):
        raise TypeError(f"{label} debe ser entero")

    if value < 1 or value > 65535:
        raise ControlPlaneValidationError(f"{label} debe estar entre 1 y 65535")


def _normalize_text_tuple(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    return tuple(
        _ensure_non_empty_text(value, f"{label}[{index}]")
        for index, value in enumerate(values)
    )


def _normalize_secret_payload(payload: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(payload, Mapping):
        raise TypeError("inline_payload debe ser un mapping")

    return {
        _ensure_non_empty_text(key, "inline_payload.key"): _ensure_non_empty_text(
            value,
            f"inline_payload.{key}",
        )
        for key, value in payload.items()
    }


def _coerce_enum(
    value: EnumValue | str,
    enum_class: type[EnumValue],
    label: str,
) -> EnumValue:
    if isinstance(value, enum_class):
        return value

    if not isinstance(value, str):
        raise TypeError(f"{label} debe ser texto")

    try:
        return enum_class(value)
    except ValueError as exc:
        allowed_values = ", ".join(member.value for member in enum_class)
        raise ControlPlaneValidationError(
            f"{label} debe ser uno de: {allowed_values}"
        ) from exc
