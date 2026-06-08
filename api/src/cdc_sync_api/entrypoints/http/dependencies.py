from cdc_sync_api.application.use_cases.check_health import CheckHealthUseCase
from cdc_sync_api.application.services.cdc_connector_compiler_registry import (
    CdcConnectorCompilerRegistry,
)
from cdc_sync_api.application.use_cases.materialize_cdc_connector import (
    MaterializeCdcConnectorUseCase,
)
from cdc_sync_api.application.use_cases.manage_control_plane import (
    ManageControlPlaneUseCase,
)
from cdc_sync_api.infrastructure.cdc.debezium_postgres_connector_compiler import (
    DebeziumPostgresConnectorCompiler,
)
from cdc_sync_api.infrastructure.kafka_connect.http_kafka_connect_client import (
    HttpKafkaConnectClient,
)
from cdc_sync_api.infrastructure.persistence.control_plane_repository import (
    SqlAlchemyControlPlaneRepository,
)
from cdc_sync_api.infrastructure.persistence.sqlalchemy import (
    SqlAlchemyDatabaseHealthChecker,
    get_engine,
)
from cdc_sync_api.shared.settings import get_settings


def get_health_use_case() -> CheckHealthUseCase:
    return CheckHealthUseCase(
        database_health_checker=SqlAlchemyDatabaseHealthChecker(get_engine()),
    )


def get_control_plane_admin_use_case() -> ManageControlPlaneUseCase:
    return ManageControlPlaneUseCase(
        repository=SqlAlchemyControlPlaneRepository(get_engine()),
    )


def get_materialize_cdc_connector_use_case() -> MaterializeCdcConnectorUseCase:
    settings = get_settings()
    return MaterializeCdcConnectorUseCase(
        repository=SqlAlchemyControlPlaneRepository(get_engine()),
        compiler_registry=CdcConnectorCompilerRegistry(
            (DebeziumPostgresConnectorCompiler(),)
        ),
        kafka_connect_client=HttpKafkaConnectClient(settings.kafka_connect_base_url),
    )
