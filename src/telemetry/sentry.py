"""Sentry error tracking with per-class rate-limiting."""

from __future__ import annotations

import time
import logging
from typing import Any
from ..logging import _CLIENT_ID, _REQUEST_ID, _SESSION_ID
from ..config.telemetry import (
    SENTRY_DSN,
    SENTRY_RELEASE,
    SENTRY_ENVIRONMENT,
    SENTRY_SAMPLE_RATE,
    SENTRY_RATE_LIMIT_S,
    SENTRY_TAG_CLIENT_ID,
    SENTRY_TAG_REQUEST_ID,
    SENTRY_TAG_SESSION_ID,
)

logger = logging.getLogger(__name__)

_error_timestamps: dict[str, float] = {}
_initialized: bool = False


def init_sentry() -> None:
    """Initialize Sentry SDK. Idempotent."""
    global _initialized  # noqa: PLW0603
    if _initialized:
        return
    import sentry_sdk

    kwargs: dict[str, Any] = {
        "dsn": SENTRY_DSN,
        "environment": SENTRY_ENVIRONMENT,
        "traces_sample_rate": 0.0,
        "sample_rate": SENTRY_SAMPLE_RATE,
        "attach_stacktrace": True,
    }
    if SENTRY_RELEASE:
        kwargs["release"] = SENTRY_RELEASE

    sentry_sdk.init(**kwargs)

    try:
        import torch

        if torch.cuda.is_available():
            sentry_sdk.set_tag("gpu.device.name", torch.cuda.get_device_name(0))
    except Exception:  # noqa: BLE001
        pass

    _initialized = True
    logger.info("Sentry initialized: environment=%s", SENTRY_ENVIRONMENT)


def shutdown_sentry() -> None:
    """Flush Sentry events. Idempotent."""
    global _initialized  # noqa: PLW0603
    if not _initialized:
        return
    try:
        import sentry_sdk

        sentry_sdk.flush(timeout=2.0)
    except Exception:  # noqa: BLE001
        pass
    _initialized = False


def capture_error(
    error: BaseException,
    *,
    session_id: str | None = None,
    request_id: str | None = None,
    client_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Report an error to Sentry with rate-limiting per error class."""
    if not _initialized:
        return

    key = type(error).__qualname__
    now = time.monotonic()
    last = _error_timestamps.get(key, 0.0)
    if (now - last) < SENTRY_RATE_LIMIT_S:
        return
    _error_timestamps[key] = now

    import sentry_sdk

    sid = session_id or _SESSION_ID.get()
    rid = request_id or _REQUEST_ID.get()
    cid = client_id or _CLIENT_ID.get()

    with sentry_sdk.push_scope() as scope:
        scope.set_tag(SENTRY_TAG_SESSION_ID, sid)
        scope.set_tag(SENTRY_TAG_REQUEST_ID, rid)
        scope.set_tag(SENTRY_TAG_CLIENT_ID, cid)
        if extra:
            for k, v in extra.items():
                scope.set_extra(k, v)
        sentry_sdk.capture_exception(error)


def add_breadcrumb(
    message: str,
    *,
    category: str,
    level: str = "info",
    data: dict[str, Any] | None = None,
) -> None:
    """Add a Sentry breadcrumb. No-op when Sentry is disabled."""
    if not _initialized:
        return
    import sentry_sdk

    sentry_sdk.add_breadcrumb(message=message, category=category, level=level, data=data or {})


__all__ = ["init_sentry", "shutdown_sentry", "capture_error", "add_breadcrumb"]
