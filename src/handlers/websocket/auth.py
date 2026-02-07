"""Authentication handler."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Security, WebSocket
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery

from ...config import TEXT_API_KEY

logger = logging.getLogger(__name__)

# API Key can be provided via query parameter or header
api_key_query = APIKeyQuery(name="api_key", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def validate_api_key(provided_key: str) -> bool:
    """Validate provided API key against configured key.

    Args:
        provided_key: The API key to validate

    Returns:
        True if valid, False otherwise
    """
    return provided_key == TEXT_API_KEY


def _select_api_key(*candidates: str | None) -> str | None:
    """Return the first non-empty API key candidate from the provided values."""
    for candidate in candidates:
        if candidate:
            return candidate
    return None


def _validate_candidate(provided_key: str | None, *, context: str) -> tuple[bool, str | None, str | None]:
    """Validate a candidate API key and return (is_valid, key, error_code)."""
    if not provided_key:
        logger.warning("%s missing API key", context)
        return False, None, "missing"
    if not validate_api_key(provided_key):
        logger.warning("%s invalid API key", context)
        return False, None, "invalid"
    return True, provided_key, None


async def get_api_key(
    api_key_query: str | None = Security(api_key_query),
    api_key_header: str | None = Security(api_key_header),
) -> str:
    """FastAPI dependency to extract and validate API key from request."""

    provided_key = _select_api_key(api_key_header, api_key_query)
    ok, valid_key, error = _validate_candidate(provided_key, context="HTTP request")
    if ok and valid_key:
        return valid_key

    if error == "missing":
        raise HTTPException(
            status_code=401, detail="API key required. Provide via 'X-API-Key' header or 'api_key' query parameter."
        )
    raise HTTPException(status_code=401, detail="Invalid API key.")


async def authenticate_websocket(websocket: WebSocket) -> bool:
    """Authenticate WebSocket connection using API key.

    Args:
        websocket: WebSocket connection to authenticate

    Returns:
        True if authenticated, False otherwise
    """
    provided_key = _select_api_key(
        websocket.headers.get("x-api-key"),
        websocket.headers.get("X-API-Key"),
        websocket.query_params.get("api_key"),
    )
    ok, _, error = _validate_candidate(provided_key, context="WebSocket connection")
    if not ok:
        return False
    logger.info("WebSocket connection authenticated successfully")
    return True


__all__ = [
    "validate_api_key",
    "get_api_key",
    "authenticate_websocket",
]
