import json
import socket
from collections.abc import Callable
from json import JSONDecodeError
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT_SECONDS = 10

Urlopen = Callable[..., object]


def fetch_worker_runtime_config(
    control_plane_base_url: str,
    worker_id: str,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    urlopen_fn: Urlopen = urlopen,
) -> dict[object, object]:
    url = build_worker_runtime_config_url(control_plane_base_url, worker_id)
    request = Request(
        url,
        headers={"Accept": "application/json"},
        method="GET",
    )

    try:
        response = urlopen_fn(request, timeout=timeout_seconds)
        raw_body = _read_context_response_body(response)
    except HTTPError as exc:
        raise RuntimeError(
            "La API del control plane devolvió "
            f"HTTP {exc.code} al cargar la configuración del worker '{worker_id}'"
        ) from exc
    except (URLError, TimeoutError, socket.timeout, OSError) as exc:
        raise RuntimeError(
            "No se pudo cargar la configuración runtime del worker "
            f"'{worker_id}' desde '{url}'"
        ) from exc

    return _decode_runtime_config(raw_body, worker_id)


def build_worker_runtime_config_url(
    control_plane_base_url: str,
    worker_id: str,
) -> str:
    return (
        f"{control_plane_base_url.rstrip('/')}/workers/"
        f"{quote(worker_id, safe='')}/config"
    )


def _read_context_response_body(response: object) -> bytes:
    if hasattr(response, "__enter__"):
        with response as context_response:
            return _read_response_body(context_response)

    return _read_response_body(response)


def _read_response_body(response: object) -> bytes:
    status = getattr(response, "status", 200)
    if status < 200 or status > 299:
        raise RuntimeError(
            f"La API del control plane devolvió HTTP {status} al cargar la configuración del worker"
        )

    body = response.read()
    if isinstance(body, bytes):
        return body

    raise TypeError("La respuesta del control plane debe ser bytes")


def _decode_runtime_config(raw_body: bytes, worker_id: str) -> dict[object, object]:
    try:
        decoded_body = raw_body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"La configuración runtime del worker '{worker_id}' no es UTF-8 válido"
        ) from exc

    try:
        payload = json.loads(decoded_body)
    except JSONDecodeError as exc:
        raise ValueError(
            f"La configuración runtime del worker '{worker_id}' no es JSON válido"
        ) from exc

    if isinstance(payload, dict):
        return payload

    raise TypeError(
        f"La configuración runtime del worker '{worker_id}' debe ser un objeto JSON"
    )
