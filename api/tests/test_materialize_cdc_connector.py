from __future__ import annotations

from typing import Mapping
from uuid import UUID, uuid4

import pytest

from cdc_sync_api.application.dto.cdc_connector_dto import (
    CdcConnectorCompileRequest,
    CompiledCdcConnector,
)
from cdc_sync_api.application.errors import ControlPlaneNotFoundError
from cdc_sync_api.application.services.cdc_connector_compiler_registry import (
    CdcConnectorCompilerRegistry,
)
from cdc_sync_api.application.use_cases.materialize_cdc_connector import (
    MaterializeCdcConnectorUseCase,
)
from cdc_sync_api.domain.control_plane import (
    ConfiguredTable,
    ControlPlaneValidationError,
    DestinationColumn,
    SecretProvider,
    SecretReference,
    SourceConnection,
    SourceType,
    SyncConfig,
    SyncMode,
)


def test_materializes_connector_with_compiler_selected_by_source_type() -> None:
    source_connection = _source_connection()
    credentials = _secret(source_connection.credentials_secret_id)
    config = _sync_config(source_connection.id)
    repository = _Repository(
        source_connections={source_connection.id: source_connection},
        secrets={credentials.id: credentials},
        configs=(config,),
    )
    compiler = _FakeConnectorCompiler()
    kafka_connect_client = _KafkaConnectClient()
    use_case = MaterializeCdcConnectorUseCase(
        repository=repository,
        compiler_registry=CdcConnectorCompilerRegistry((compiler,)),
        kafka_connect_client=kafka_connect_client,
    )

    response = use_case.materialize_source_connector(source_connection.id)

    assert compiler.received_request is not None
    assert compiler.received_request.source_connection == source_connection
    assert compiler.received_request.credentials == credentials
    assert compiler.received_request.configs == (config,)
    assert kafka_connect_client.calls == (
        ("fake-connector", {"connector.class": "example.FakeConnector"}),
    )
    assert response.connector_name == "fake-connector"
    assert response.connector_class == "example.FakeConnector"
    assert response.source_type == "postgresql"
    assert not hasattr(response, "config")


def test_materialization_fails_without_registered_compiler() -> None:
    source_connection = _source_connection()
    credentials = _secret(source_connection.credentials_secret_id)
    repository = _Repository(
        source_connections={source_connection.id: source_connection},
        secrets={credentials.id: credentials},
        configs=(),
    )
    use_case = MaterializeCdcConnectorUseCase(
        repository=repository,
        compiler_registry=CdcConnectorCompilerRegistry(()),
        kafka_connect_client=_KafkaConnectClient(),
    )

    with pytest.raises(ControlPlaneValidationError, match="No existe compilador CDC"):
        use_case.materialize_source_connector(source_connection.id)


def test_materialization_fails_without_source_credentials() -> None:
    source_connection = _source_connection()
    repository = _Repository(
        source_connections={source_connection.id: source_connection},
        secrets={},
        configs=(),
    )
    use_case = MaterializeCdcConnectorUseCase(
        repository=repository,
        compiler_registry=CdcConnectorCompilerRegistry((_FakeConnectorCompiler(),)),
        kafka_connect_client=_KafkaConnectClient(),
    )

    with pytest.raises(ControlPlaneValidationError, match="credenciales"):
        use_case.materialize_source_connector(source_connection.id)


def test_materialization_fails_when_source_does_not_exist() -> None:
    use_case = MaterializeCdcConnectorUseCase(
        repository=_Repository(source_connections={}, secrets={}, configs=()),
        compiler_registry=CdcConnectorCompilerRegistry((_FakeConnectorCompiler(),)),
        kafka_connect_client=_KafkaConnectClient(),
    )

    with pytest.raises(ControlPlaneNotFoundError, match="conexión de origen"):
        use_case.materialize_source_connector(uuid4())


class _FakeConnectorCompiler:
    source_type = SourceType.POSTGRESQL

    def __init__(self) -> None:
        self.received_request: CdcConnectorCompileRequest | None = None

    def compile(
        self,
        request: CdcConnectorCompileRequest,
    ) -> CompiledCdcConnector:
        self.received_request = request
        return CompiledCdcConnector(
            connector_name="fake-connector",
            source_connection_id=request.source_connection.id,
            source_type=request.source_connection.source_type,
            connector_class="example.FakeConnector",
            topic_prefix="fake",
            captured_tables=("public.customers",),
            config={"connector.class": "example.FakeConnector"},
        )


class _KafkaConnectClient:
    def __init__(self) -> None:
        self.calls: tuple[tuple[str, dict[str, str]], ...] = ()

    def put_connector_config(
        self,
        connector_name: str,
        config: Mapping[str, str],
    ) -> None:
        self.calls = self.calls + ((connector_name, dict(config)),)


class _Repository:
    def __init__(
        self,
        *,
        source_connections: dict[UUID, SourceConnection],
        secrets: dict[UUID, SecretReference],
        configs: tuple[SyncConfig, ...],
    ) -> None:
        self._source_connections = source_connections
        self._secrets = secrets
        self._configs = configs

    def get_source_connection(
        self,
        source_connection_id: UUID,
    ) -> SourceConnection | None:
        return self._source_connections.get(source_connection_id)

    def get_secret_reference(self, secret_id: UUID) -> SecretReference | None:
        return self._secrets.get(secret_id)

    def list_configs(self) -> tuple[SyncConfig, ...]:
        return self._configs


def _source_connection() -> SourceConnection:
    return SourceConnection(
        id=uuid4(),
        name="PostgreSQL local",
        source_type=SourceType.POSTGRESQL,
        host="postgres",
        port=5432,
        database_name="cdc_sync",
        credentials_secret_id=uuid4(),
    )


def _secret(secret_id: UUID) -> SecretReference:
    return SecretReference(
        id=secret_id,
        name=f"source-{secret_id}",
        provider=SecretProvider.INLINE,
        inline_payload={"user": "cdc_sync", "password": "cdc_sync"},
    )


def _sync_config(source_connection_id: UUID) -> SyncConfig:
    return SyncConfig(
        id=uuid4(),
        name="Config local",
        source_connection_id=source_connection_id,
        destination_id=uuid4(),
        sync_mode=SyncMode.REALTIME,
        tables=(
            ConfiguredTable(
                id=uuid4(),
                logical_name="customers",
                source_schema="public",
                source_table="customers",
                cdc_topic="cdc_sync.public.customers",
                destination_table="customers",
                primary_key_fields=("id",),
                destination_columns=(
                    DestinationColumn(
                        name="id",
                        destination_type="UInt64",
                        nullable=False,
                    ),
                ),
            ),
        ),
    )
