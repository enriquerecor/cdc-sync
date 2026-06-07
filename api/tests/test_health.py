from fastapi.testclient import TestClient

from cdc_sync_api.application.ports.database_health_checker import (
    DependencyUnavailableError,
)
from cdc_sync_api.application.use_cases.check_health import CheckHealthUseCase
from cdc_sync_api.entrypoints.http.app import build_app
from cdc_sync_api.entrypoints.http.dependencies import get_health_use_case
from cdc_sync_api.shared.settings import get_settings


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


def test_health_allows_local_frontend_origin() -> None:
    get_settings.cache_clear()
    app = build_app()
    app.dependency_overrides[get_health_use_case] = lambda: CheckHealthUseCase(
        HealthyChecker()
    )
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
