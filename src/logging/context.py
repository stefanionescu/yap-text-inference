"""Logging context helpers for consistent structured fields."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

_SESSION_ID: ContextVar[str] = ContextVar("session_id", default="-")
_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")
_CLIENT_ID: ContextVar[str] = ContextVar("client_id", default="-")


def set_log_context(
    *,
    session_id: str | None = None,
    request_id: str | None = None,
    client_id: str | None = None,
) -> list[tuple[ContextVar[str], object]]:
    """Set log context values and return tokens for reset."""
    tokens: list[tuple[ContextVar[str], object]] = []
    if session_id is not None:
        tokens.append((_SESSION_ID, _SESSION_ID.set(session_id)))
    if request_id is not None:
        tokens.append((_REQUEST_ID, _REQUEST_ID.set(request_id)))
    if client_id is not None:
        tokens.append((_CLIENT_ID, _CLIENT_ID.set(client_id)))
    return tokens


def reset_log_context(tokens: list[tuple[ContextVar[str], object]]) -> None:
    """Reset log context values using tokens returned by set_log_context."""
    for var, token in tokens:
        var.reset(token)


@contextmanager
def log_context(
    *,
    session_id: str | None = None,
    request_id: str | None = None,
    client_id: str | None = None,
) -> Iterator[None]:
    """Context manager for applying log fields within a block."""
    tokens = set_log_context(
        session_id=session_id,
        request_id=request_id,
        client_id=client_id,
    )
    try:
        yield
    finally:
        reset_log_context(tokens)


def install_log_context() -> None:
    """Install a LogRecord factory that injects context fields."""
    if getattr(install_log_context, "_installed", False):
        return

    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.session_id = _SESSION_ID.get()
        record.request_id = _REQUEST_ID.get()
        record.client_id = _CLIENT_ID.get()
        return record

    logging.setLogRecordFactory(record_factory)
    install_log_context._installed = True


__all__ = [
    "install_log_context",
    "log_context",
    "reset_log_context",
    "set_log_context",
]
