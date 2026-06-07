from __future__ import annotations

import json
from typing import Any

from fastapi.testclient import TestClient

from cdc_sync_api.entrypoints.http.app import build_app


EXPECTED_OPERATIONS = {
    ("/api/v1", "get"): "Descubrir API",
    ("/api/v1/workers", "get"): "Listar workers",
    ("/api/v1/workers", "post"): "Crear worker",
    ("/api/v1/workers/{worker_internal_id}", "get"): "Consultar worker",
    ("/api/v1/workers/{worker_internal_id}", "put"): "Actualizar worker",
    ("/api/v1/workers/{worker_internal_id}", "delete"): "Eliminar worker",
    (
        "/api/v1/workers/{worker_internal_id}/config-assignment",
        "put",
    ): "Asignar configuración efectiva",
    ("/api/v1/source-connections", "get"): "Listar conexiones de origen",
    ("/api/v1/source-connections", "post"): "Crear conexión de origen",
    (
        "/api/v1/source-connections/{source_connection_id}",
        "get",
    ): "Consultar conexión de origen",
    (
        "/api/v1/source-connections/{source_connection_id}",
        "put",
    ): "Actualizar conexión de origen",
    (
        "/api/v1/source-connections/{source_connection_id}",
        "delete",
    ): "Eliminar conexión de origen",
    (
        "/api/v1/source-connections/{source_connection_id}/cdc-connector",
        "put",
    ): "Materializar conector CDC",
    ("/api/v1/destinations", "get"): "Listar destinos",
    ("/api/v1/destinations", "post"): "Crear destino",
    ("/api/v1/destinations/{destination_id}", "get"): "Consultar destino",
    ("/api/v1/destinations/{destination_id}", "put"): "Actualizar destino",
    ("/api/v1/destinations/{destination_id}", "delete"): "Eliminar destino",
    ("/api/v1/configs", "get"): "Listar configuraciones",
    ("/api/v1/configs", "post"): "Crear configuración",
    ("/api/v1/configs/{config_id}", "get"): "Consultar configuración",
    ("/api/v1/configs/{config_id}", "put"): "Actualizar configuración",
    ("/api/v1/configs/{config_id}", "delete"): "Eliminar configuración",
    ("/workers/{worker_id}/config", "get"): "Obtener configuración runtime",
    ("/health", "get"): "Comprobar salud",
}

SCHEMAS_WITH_EXAMPLES = (
    "WorkerRequest",
    "WorkerResponse",
    "SourceConnectionCreateRequest",
    "SourceConnectionResponse",
    "DestinationCreateRequest",
    "DestinationResponse",
    "SyncConfigRequest",
    "SyncConfigResponse",
    "AssignmentRequest",
    "AssignmentResponse",
    "CdcConnectorMaterializationResponse",
    "WorkerRuntimeConfigResponse",
)

ADMIN_RESPONSE_SCHEMAS = (
    "WorkerResponse",
    "SourceConnectionResponse",
    "DestinationResponse",
    "SyncConfigResponse",
    "AssignmentResponse",
    "CdcConnectorMaterializationResponse",
)


def test_openapi_exposes_control_plane_and_runtime_paths() -> None:
    schema = _openapi_schema()

    for path, method in EXPECTED_OPERATIONS:
        assert path in schema["paths"]
        assert method in schema["paths"][path]


def test_openapi_operations_have_useful_metadata() -> None:
    schema = _openapi_schema()

    for (path, method), expected_summary in EXPECTED_OPERATIONS.items():
        operation = schema["paths"][path][method]

        assert operation["summary"] == expected_summary
        assert operation["description"].strip()
        assert operation["tags"]


def test_openapi_schemas_include_examples_for_public_contracts() -> None:
    schemas = _openapi_schema()["components"]["schemas"]

    for schema_name in SCHEMAS_WITH_EXAMPLES:
        assert _schema_examples(schemas[schema_name]), schema_name


def test_openapi_runtime_contract_exposes_source_schema_alias() -> None:
    schemas = _openapi_schema()["components"]["schemas"]
    source_properties = schemas["RuntimeTableSourceResponse"]["properties"]
    runtime_example = schemas["WorkerRuntimeConfigResponse"]["examples"][0]

    assert "schema" in source_properties
    assert "source_schema" not in source_properties
    assert runtime_example["tables"]["customers"]["source"]["schema"] == "public"


def test_openapi_admin_response_schemas_do_not_expose_secrets() -> None:
    schemas = _openapi_schema()["components"]["schemas"]

    for schema_name in ADMIN_RESPONSE_SCHEMAS:
        serialized_schema = json.dumps(schemas[schema_name])

        assert "password" not in serialized_schema
        assert "credentials_secret_id" not in serialized_schema
        assert "inline_payload" not in serialized_schema


def _openapi_schema() -> dict[str, Any]:
    response = TestClient(build_app()).get("/openapi.json")

    assert response.status_code == 200
    return response.json()


def _schema_examples(schema: dict[str, Any]) -> list[dict[str, Any]]:
    examples = schema.get("examples", [])
    if isinstance(examples, list):
        return examples

    return []
