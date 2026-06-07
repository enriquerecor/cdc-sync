from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from control_plane_client import (
    build_worker_runtime_config_url,
    fetch_worker_runtime_config,
)


@dataclass
class FakeResponse:
    body: bytes
    status: int = 200

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_build_worker_runtime_config_url_quotes_worker_id() -> None:
    url = build_worker_runtime_config_url(
        "http://localhost:8000/",
        "worker/local 1",
    )

    assert url == "http://localhost:8000/workers/worker%2Flocal%201/config"


def test_fetch_worker_runtime_config_returns_json_object() -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["accept"] = request.headers["Accept"]
        return FakeResponse(b'{"contract_version":1}')

    payload = fetch_worker_runtime_config(
        "http://localhost:8000",
        "local-worker",
        urlopen_fn=fake_urlopen,
    )

    assert captured == {
        "url": "http://localhost:8000/workers/local-worker/config",
        "timeout": 10,
        "accept": "application/json",
    }
    assert payload == {"contract_version": 1}


def test_fetch_worker_runtime_config_fails_with_http_error() -> None:
    def fake_urlopen(_: Request, timeout: float) -> FakeResponse:
        assert timeout == 10
        raise HTTPError(
            url="http://localhost:8000/workers/local-worker/config",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

    with pytest.raises(RuntimeError, match="HTTP 404"):
        fetch_worker_runtime_config(
            "http://localhost:8000",
            "local-worker",
            urlopen_fn=fake_urlopen,
        )


def test_fetch_worker_runtime_config_fails_when_api_is_unavailable() -> None:
    def fake_urlopen(_: Request, timeout: float) -> FakeResponse:
        assert timeout == 10
        raise URLError("connection refused")

    with pytest.raises(
        RuntimeError,
        match="No se pudo cargar la configuración runtime",
    ):
        fetch_worker_runtime_config(
            "http://localhost:8000",
            "local-worker",
            urlopen_fn=fake_urlopen,
        )


def test_fetch_worker_runtime_config_fails_with_timeout() -> None:
    def fake_urlopen(_: Request, timeout: float) -> FakeResponse:
        assert timeout == 10
        raise TimeoutError("timed out")

    with pytest.raises(
        RuntimeError,
        match="No se pudo cargar la configuración runtime",
    ):
        fetch_worker_runtime_config(
            "http://localhost:8000",
            "local-worker",
            urlopen_fn=fake_urlopen,
        )


def test_fetch_worker_runtime_config_fails_with_invalid_json() -> None:
    with pytest.raises(ValueError, match="no es JSON válido"):
        fetch_worker_runtime_config(
            "http://localhost:8000",
            "local-worker",
            urlopen_fn=lambda *_, **__: FakeResponse(b"{invalid json"),
        )


def test_fetch_worker_runtime_config_fails_when_json_is_not_object() -> None:
    with pytest.raises(TypeError, match="debe ser un objeto JSON"):
        fetch_worker_runtime_config(
            "http://localhost:8000",
            "local-worker",
            urlopen_fn=lambda *_, **__: FakeResponse(b"[]"),
        )


def test_fetch_worker_runtime_config_fails_with_non_success_status() -> None:
    with pytest.raises(RuntimeError, match="HTTP 500"):
        fetch_worker_runtime_config(
            "http://localhost:8000",
            "local-worker",
            urlopen_fn=lambda *_, **__: FakeResponse(b"{}", status=500),
        )
