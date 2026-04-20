from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from cdc_sync_api.application.dto.editing_config_dto import EditingConfigDto
from cdc_sync_api.application.errors import EditingConfigConflictError
from cdc_sync_api.application.use_cases.delete_editing_config import (
    DeleteEditingConfigUseCase,
)
from cdc_sync_api.application.use_cases.get_editing_config import (
    GetEditingConfigUseCase,
)
from cdc_sync_api.application.use_cases.save_editing_config import (
    SaveEditingConfigUseCase,
)
from cdc_sync_api.entrypoints.http.app import build_app
from cdc_sync_api.entrypoints.http.dependencies import (
    get_delete_editing_config_use_case,
    get_editing_config_use_case,
    get_save_editing_config_use_case,
)


class InMemoryEditingConfigRepository:
    def __init__(self) -> None:
        self._config: EditingConfigDto | None = None
        self._revision = 0

    def get(self) -> EditingConfigDto | None:
        return self._config

    def save(
        self,
        *,
        config: EditingConfigDto,
        expected_version: int | None,
    ) -> EditingConfigDto:
        if self._config is None:
            if expected_version is not None:
                raise EditingConfigConflictError(
                    "No existe configuración en edición para la version indicada"
                )
        else:
            if expected_version is None:
                raise EditingConfigConflictError(
                    "Debe indicar expected_version para sobrescribir la configuración en edición"
                )

            if self._config.version != expected_version:
                raise EditingConfigConflictError(
                    "La configuración en edición fue modificada por otra operación"
                )

        self._revision += 1
        persisted_updated_at = datetime(2026, 4, 19, 18, 0, tzinfo=UTC) + timedelta(
            seconds=self._revision
        )
        self._config = replace(
            config,
            version=self._revision,
            updated_at=persisted_updated_at,
        )
        return self._config

    def delete(self, *, expected_version: int | None) -> bool:
        if self._config is None:
            return False

        if expected_version is None:
            raise EditingConfigConflictError(
                "Debe indicar expected_version para borrar la configuración en edición"
            )

        if self._config.version != expected_version:
            raise EditingConfigConflictError(
                "La configuración en edición fue modificada por otra operación"
            )

        self._config = None
        return True


def test_editing_config_put_get_and_delete_happy_path() -> None:
    repository = InMemoryEditingConfigRepository()
    client = _build_client(repository)

    put_response = client.put("/api/v1/editing-config", json=_build_valid_payload())

    assert put_response.status_code == 200
    body = put_response.json()
    assert body["version"] == 1
    assert body["source_connections"][0]["name"] == "postgres_local"
    assert body["tables"][0]["sync"]["mode"] == "realtime"
    assert body["updated_at"]

    get_response = client.get("/api/v1/editing-config")

    assert get_response.status_code == 200
    assert get_response.json() == body

    delete_response = client.delete(
        "/api/v1/editing-config",
        params={"expected_version": body["version"]},
    )

    assert delete_response.status_code == 204

    missing_response = client.get("/api/v1/editing-config")

    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "No existe configuración en edición"}


def test_editing_config_put_returns_422_when_sync_mode_is_invalid() -> None:
    repository = InMemoryEditingConfigRepository()
    client = _build_client(repository)
    payload = _build_valid_payload()
    payload["tables"][0]["sync"]["mode"] = "snapshot"

    response = client.put("/api/v1/editing-config", json=payload)

    assert response.status_code == 422
    assert response.json() == {
        "detail": "La tabla 'customers'.sync.mode solo admite realtime"
    }
    assert repository.get() is None


def test_editing_config_put_returns_409_when_expected_version_is_missing() -> None:
    repository = InMemoryEditingConfigRepository()
    client = _build_client(repository)
    created_response = client.put("/api/v1/editing-config", json=_build_valid_payload())

    assert created_response.status_code == 200

    stale_response = client.put("/api/v1/editing-config", json=_build_valid_payload())

    assert stale_response.status_code == 409
    assert stale_response.json() == {
        "detail": "Debe indicar expected_version para sobrescribir la configuración en edición"
    }


def test_editing_config_delete_returns_409_when_expected_version_is_stale() -> None:
    repository = InMemoryEditingConfigRepository()
    client = _build_client(repository)

    first_response = client.put("/api/v1/editing-config", json=_build_valid_payload())
    assert first_response.status_code == 200
    stale_version = first_response.json()["version"]

    second_payload = _build_valid_payload()
    second_payload["expected_version"] = stale_version
    second_response = client.put("/api/v1/editing-config", json=second_payload)
    assert second_response.status_code == 200

    delete_response = client.delete(
        "/api/v1/editing-config",
        params={"expected_version": stale_version},
    )

    assert delete_response.status_code == 409
    assert delete_response.json() == {
        "detail": "La configuración en edición fue modificada por otra operación"
    }


def test_editing_config_put_accepts_expected_version() -> None:
    repository = InMemoryEditingConfigRepository()
    client = _build_client(repository)

    created_response = client.put("/api/v1/editing-config", json=_build_valid_payload())
    assert created_response.status_code == 200

    payload = _build_valid_payload()
    payload["expected_version"] = 1

    updated_response = client.put("/api/v1/editing-config", json=payload)

    assert updated_response.status_code == 200
    assert updated_response.json()["version"] == 2


def test_editing_config_delete_accepts_expected_version() -> None:
    repository = InMemoryEditingConfigRepository()
    client = _build_client(repository)

    created_response = client.put("/api/v1/editing-config", json=_build_valid_payload())
    assert created_response.status_code == 200

    delete_response = client.delete(
        "/api/v1/editing-config",
        params={"expected_version": 1},
    )

    assert delete_response.status_code == 204


def test_editing_config_recreate_keeps_version_monotonic_after_delete() -> None:
    repository = InMemoryEditingConfigRepository()
    client = _build_client(repository)

    first_response = client.put("/api/v1/editing-config", json=_build_valid_payload())
    assert first_response.status_code == 200
    first_version = first_response.json()["version"]

    delete_response = client.delete(
        "/api/v1/editing-config",
        params={"expected_version": first_version},
    )
    assert delete_response.status_code == 204

    recreated_response = client.put("/api/v1/editing-config", json=_build_valid_payload())
    assert recreated_response.status_code == 200
    recreated_version = recreated_response.json()["version"]

    assert recreated_version > first_version

    stale_put_payload = _build_valid_payload()
    stale_put_payload["expected_version"] = first_version

    stale_put_response = client.put("/api/v1/editing-config", json=stale_put_payload)

    assert stale_put_response.status_code == 409
    assert stale_put_response.json() == {
        "detail": "La configuración en edición fue modificada por otra operación"
    }

    stale_delete_response = client.delete(
        "/api/v1/editing-config",
        params={"expected_version": first_version},
    )

    assert stale_delete_response.status_code == 409
    assert stale_delete_response.json() == {
        "detail": "La configuración en edición fue modificada por otra operación"
    }


def _build_client(repository: InMemoryEditingConfigRepository) -> TestClient:
    app = build_app()
    app.dependency_overrides[get_editing_config_use_case] = lambda: GetEditingConfigUseCase(
        repository
    )
    app.dependency_overrides[get_save_editing_config_use_case] = lambda: SaveEditingConfigUseCase(
        repository
    )
    app.dependency_overrides[
        get_delete_editing_config_use_case
    ] = lambda: DeleteEditingConfigUseCase(repository)
    return TestClient(app)


def _build_valid_payload() -> dict[str, object]:
    return {
        "expected_version": None,
        "source_connections": [
            {
                "name": "postgres_local",
                "host": "postgres",
                "port": 5432,
                "database": "cdc_sync",
                "username": "cdc_sync",
                "password": "cdc_sync",
            }
        ],
        "tables": [
            {
                "name": "customers",
                "enabled": True,
                "source": {
                    "adapter": "debezium_postgres",
                    "connection": "postgres_local",
                    "schema": "public",
                    "table": "customers",
                    "topic": "cdc_sync.public.customers",
                },
                "pk": ["id"],
                "sync": {
                    "mode": "realtime",
                },
                "destination": {
                    "table": "customers",
                    "default_nullable": True,
                    "columns": [
                        {
                            "name": "id",
                            "type": "UInt64",
                            "nullable": False,
                        },
                        {
                            "name": "email",
                            "type": "String",
                        },
                    ],
                },
            }
        ],
    }
