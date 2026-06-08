from __future__ import annotations

from cdc_sync_api.domain.control_plane import (
    Destination,
    SourceConnection,
    SyncConfig,
    Worker,
)


def worker_values(worker: Worker) -> dict[str, object]:
    return {
        "id": worker.id,
        "worker_id": worker.worker_id,
        "name": worker.name,
        "description": worker.description,
        "kafka_group_id": worker.kafka_group_id,
        "enabled": worker.enabled,
    }


def source_connection_values(
    source_connection: SourceConnection,
) -> dict[str, object]:
    return {
        "id": source_connection.id,
        "name": source_connection.name,
        "source_type": source_connection.source_type.value,
        "host": source_connection.host,
        "port": source_connection.port,
        "database_name": source_connection.database_name,
        "credentials_secret_id": source_connection.credentials_secret_id,
    }


def destination_values(destination: Destination) -> dict[str, object]:
    return {
        "id": destination.id,
        "name": destination.name,
        "destination_type": destination.destination_type.value,
        "host": destination.host,
        "port": destination.port,
        "secure": destination.secure,
        "database_name": destination.database_name,
        "credentials_secret_id": destination.credentials_secret_id,
    }


def config_values(config: SyncConfig) -> dict[str, object]:
    return {
        "id": config.id,
        "name": config.name,
        "source_connection_id": config.source_connection_id,
        "destination_id": config.destination_id,
        "sync_mode": config.sync_mode.value,
        "enabled": config.enabled,
    }


def build_worker(row) -> Worker:
    return Worker(
        id=row["id"],
        worker_id=row["worker_id"],
        name=row["name"],
        description=row["description"],
        kafka_group_id=row["kafka_group_id"],
        enabled=row["enabled"],
    )


def build_source_connection(row) -> SourceConnection:
    return SourceConnection(
        id=row["id"],
        name=row["name"],
        source_type=row["source_type"],
        host=row["host"],
        port=row["port"],
        database_name=row["database_name"],
        credentials_secret_id=row["credentials_secret_id"],
    )


def build_destination(row) -> Destination:
    return Destination(
        id=row["id"],
        name=row["name"],
        destination_type=row["destination_type"],
        host=row["host"],
        port=row["port"],
        secure=row["secure"],
        database_name=row["database_name"],
        credentials_secret_id=row["credentials_secret_id"],
    )
