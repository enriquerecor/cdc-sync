from cdc_sync_api.domain.control_plane import Worker

DEFAULT_WORKER_KAFKA_GROUP_PREFIX = "cdc-sync-worker"


def effective_worker_kafka_group_id(worker: Worker) -> str:
    if worker.kafka_group_id is not None:
        return worker.kafka_group_id

    return f"{DEFAULT_WORKER_KAFKA_GROUP_PREFIX}-{worker.worker_id}"
