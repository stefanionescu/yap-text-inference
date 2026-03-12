"""Authentication handler."""

from __future__ import annotations

import hmac
import time
import logging
from collections import deque
from dataclasses import dataclass
from ...config import TEXT_API_KEY
from collections.abc import Callable
from fastapi.security.api_key import APIKeyHeader
from fastapi import Request, Security, WebSocket, HTTPException
from ...config.websocket import WS_ALLOWED_ORIGINS, WS_RATE_LIMIT_WINDOW, WS_MAX_AUTH_FAILURES_PER_WINDOW

logger = logging.getLogger(__name__)

# API Key can be provided via explicit header or Authorization bearer token.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_AUTH_FAILURES: dict[str, deque[float]] = {}


@dataclass(frozen=True)
class AuthRuntimeConfig:
    """Runtime-auth settings used by HTTP and WebSocket auth flows."""

    text_api_key: str | None = TEXT_API_KEY
    allowed_origins: tuple[str, ...] = WS_ALLOWED_ORIGINS
    rate_limit_window_seconds: float = WS_RATE_LIMIT_WINDOW
    max_auth_failures_per_window: int = WS_MAX_AUTH_FAILURES_PER_WINDOW


DEFAULT_AUTH_RUNTIME_CONFIG = AuthRuntimeConfig()


def _extract_bearer_key(value: str | None) -> str | None:
    """Extract bearer token value from an Authorization header."""
    if not value:
        return None
    prefix = "bearer "
    normalized = value.strip()
    if len(normalized) <= len(prefix) or normalized[: len(prefix)].lower() != prefix:
        return None
    token = normalized[len(prefix) :].strip()
    return token or None


def _select_api_key(*candidates: str | None) -> str | None:
    """Return the first non-empty API key candidate from the provided values."""
    for candidate in candidates:
        if candidate:
            return candidate
    return None


def _validate_candidate(
    provided_key: str | None,
    *,
    context: str,
    auth_config: AuthRuntimeConfig,
) -> tuple[bool, str | None, str]:
    """Validate a candidate API key and return (is_valid, key, error_code)."""
    if not provided_key:
        logger.warning("%s missing API key", context)
        return False, None, "missing"
    if not validate_api_key(provided_key, configured_api_key=auth_config.text_api_key):
        logger.warning("%s invalid API key", context)
        return False, None, "invalid"
    return True, provided_key, ""


def _client_failure_key(client_host: str | None) -> str:
    return (client_host or "unknown").strip() or "unknown"


def _prune_failures(
    client_key: str,
    now: float,
    *,
    auth_config: AuthRuntimeConfig,
    auth_failures: dict[str, deque[float]],
) -> deque[float]:
    entries = auth_failures.setdefault(client_key, deque())
    cutoff = now - auth_config.rate_limit_window_seconds
    while entries and entries[0] <= cutoff:
        entries.popleft()
    return entries


def _is_auth_throttled(
    client_key: str,
    *,
    auth_config: AuthRuntimeConfig,
    auth_failures: dict[str, deque[float]],
    now_fn: Callable[[], float],
) -> bool:
    now = now_fn()
    entries = _prune_failures(client_key, now, auth_config=auth_config, auth_failures=auth_failures)
    return len(entries) >= auth_config.max_auth_failures_per_window


def _record_auth_failure(
    client_key: str,
    *,
    auth_config: AuthRuntimeConfig,
    auth_failures: dict[str, deque[float]],
    now_fn: Callable[[], float],
) -> None:
    now = now_fn()
    entries = _prune_failures(client_key, now, auth_config=auth_config, auth_failures=auth_failures)
    entries.append(now)


def _clear_auth_failures(client_key: str, *, auth_failures: dict[str, deque[float]]) -> None:
    auth_failures.pop(client_key, None)


def _is_origin_allowed(origin: str | None, *, allowed_origins: tuple[str, ...]) -> bool:
    """Allow non-browser clients (no Origin) and enforce allowlist for browser origins."""
    if origin is None:
        return True
    if not allowed_origins:
        return True
    return origin in allowed_origins


def _request_client_key(request: Request) -> str:
    client = request.client
    host = client.host if client else None
    return _client_failure_key(host)


def _websocket_client_key(websocket: WebSocket) -> str:
    client = websocket.client
    host = client.host if client else None
    return _client_failure_key(host)


def validate_api_key(
    provided_key: str,
    *,
    configured_api_key: str | None = TEXT_API_KEY,
) -> bool:
    """Validate provided API key against configured key.

    Args:
        provided_key: The API key to validate

    Returns:
        True if valid, False otherwise
    """
    if not configured_api_key:
        return False
    return hmac.compare_digest(provided_key, configured_api_key)


async def get_api_key(
    request: Request,
    api_key_header: str | None = Security(api_key_header),
    *,
    auth_config: AuthRuntimeConfig = DEFAULT_AUTH_RUNTIME_CONFIG,
    auth_failures: dict[str, deque[float]] | None = None,
    now_fn: Callable[[], float] = time.monotonic,
) -> str:
    """FastAPI dependency to extract and validate API key from request."""
    failures = _AUTH_FAILURES if auth_failures is None else auth_failures
    client_key = _request_client_key(request)
    if _is_auth_throttled(client_key, auth_config=auth_config, auth_failures=failures, now_fn=now_fn):
        raise HTTPException(status_code=429, detail="Too many authentication failures. Retry later.")

    bearer_key = _extract_bearer_key(request.headers.get("authorization"))
    provided_key = _select_api_key(api_key_header, bearer_key)
    ok, valid_key, error = _validate_candidate(provided_key, context="HTTP request", auth_config=auth_config)
    if ok and valid_key:
        _clear_auth_failures(client_key, auth_failures=failures)
        return valid_key

    _record_auth_failure(client_key, auth_config=auth_config, auth_failures=failures, now_fn=now_fn)

    if error == "missing":
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide via 'X-API-Key' header or 'Authorization: Bearer <key>'.",
        )
    raise HTTPException(status_code=401, detail="Invalid API key.")


async def authenticate_websocket(
    websocket: WebSocket,
    *,
    auth_config: AuthRuntimeConfig = DEFAULT_AUTH_RUNTIME_CONFIG,
    auth_failures: dict[str, deque[float]] | None = None,
    now_fn: Callable[[], float] = time.monotonic,
) -> bool:
    """Authenticate WebSocket connection using API key.

    Args:
        websocket: WebSocket connection to authenticate

    Returns:
        True if authenticated, False otherwise
    """
    failures = _AUTH_FAILURES if auth_failures is None else auth_failures
    client_key = _websocket_client_key(websocket)
    if _is_auth_throttled(client_key, auth_config=auth_config, auth_failures=failures, now_fn=now_fn):
        logger.warning("WebSocket auth throttled client=%s", client_key)
        return False

    origin = websocket.headers.get("origin")
    if not _is_origin_allowed(origin, allowed_origins=auth_config.allowed_origins):
        logger.warning("WebSocket origin rejected client=%s origin=%r", client_key, origin)
        _record_auth_failure(client_key, auth_config=auth_config, auth_failures=failures, now_fn=now_fn)
        return False

    provided_key = _select_api_key(
        websocket.headers.get("x-api-key"),
        _extract_bearer_key(websocket.headers.get("authorization")),
    )
    ok, _, error = _validate_candidate(provided_key, context="WebSocket connection", auth_config=auth_config)
    if not ok:
        _record_auth_failure(client_key, auth_config=auth_config, auth_failures=failures, now_fn=now_fn)
        return False
    _clear_auth_failures(client_key, auth_failures=failures)
    logger.info("WebSocket connection authenticated successfully")
    return True


__all__ = [
    "AuthRuntimeConfig",
    "DEFAULT_AUTH_RUNTIME_CONFIG",
    "validate_api_key",
    "get_api_key",
    "authenticate_websocket",
]
