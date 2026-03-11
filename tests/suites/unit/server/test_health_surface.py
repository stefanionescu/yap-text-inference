"""Unit tests for the internal health surface."""

from __future__ import annotations

import pytest
from src.server import create_app
from starlette.requests import Request
from fastapi import FastAPI, HTTPException
from src.helpers.health import is_health_client_allowed, parse_health_allowed_cidrs, ensure_internal_health_request


def _request_with_client(host: str | None) -> Request:
    scope = {
        "type": "http",
        "app": FastAPI(),
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/healthz",
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "client": None if host is None else (host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


def test_parse_health_allowed_cidrs_requires_at_least_one_value() -> None:
    with pytest.raises(ValueError, match="HEALTH_ALLOWED_CIDRS must contain at least one CIDR"):
        parse_health_allowed_cidrs(" , ")


def test_parse_health_allowed_cidrs_rejects_invalid_entry() -> None:
    with pytest.raises(ValueError):
        parse_health_allowed_cidrs("127.0.0.1/32,definitely-not-a-cidr")


def test_is_health_client_allowed_accepts_loopback() -> None:
    allowed_cidrs = parse_health_allowed_cidrs("127.0.0.1/32,::1/128")
    assert is_health_client_allowed("127.0.0.1", allowed_cidrs=allowed_cidrs) is True
    assert is_health_client_allowed("::1", allowed_cidrs=allowed_cidrs) is True


def test_is_health_client_allowed_rejects_public_ip() -> None:
    allowed_cidrs = parse_health_allowed_cidrs("127.0.0.1/32")
    assert is_health_client_allowed("198.51.100.10", allowed_cidrs=allowed_cidrs) is False


def test_is_health_client_allowed_accepts_configured_private_range() -> None:
    allowed_cidrs = parse_health_allowed_cidrs("10.0.0.0/8")
    assert is_health_client_allowed("10.42.0.15", allowed_cidrs=allowed_cidrs) is True


def test_ensure_internal_health_request_returns_404_for_public_client() -> None:
    request = _request_with_client("198.51.100.10")
    allowed_cidrs = parse_health_allowed_cidrs("127.0.0.1/32")
    with pytest.raises(HTTPException) as exc:
        ensure_internal_health_request(request, allowed_cidrs=allowed_cidrs)
    assert exc.value.status_code == 404


def test_create_app_disables_generated_docs_and_public_root_routes() -> None:
    app = create_app(attach_lifecycle=False, validate_environment=False)
    paths = {route.path for route in app.routes}

    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
    assert "/" not in paths
    assert "/health" not in paths
    assert "/healthz" in paths
    assert "/ws" in paths
