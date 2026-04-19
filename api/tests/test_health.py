from fastapi.testclient import TestClient

from cdc_sync_api.application.ports.database_health_checker import (
    DependencyUnavailableError,
)
from cdc_sync_api.application.use_cases.check_health import CheckHealthUseCase
from cdc_sync_api.entrypoints.http.app import build_app
from cdc_sync_api.entrypoints.http.dependencies import get_health_use_case


class HealthyChecker:
    def ensure_available(self) -> None:
        return None


class FailingChecker:
    def ensure_available(self) -> None:
        raise DependencyUnavailableError("Base de datos caída")


def test_health_returns_ok_when_database_is_available() -> None:
    app = build_app()
    app.dependency_overrides[get_health_use_case] = lambda: CheckHealthUseCase(
        HealthyChecker()
    )
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok"},
    }


def test_health_returns_503_when_database_is_not_available() -> None:
    app = build_app()
    app.dependency_overrides[get_health_use_case] = lambda: CheckHealthUseCase(
        FailingChecker()
    )
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Base de datos caída"}
