"""Telemetry lifecycle orchestration (init / shutdown)."""

from __future__ import annotations

import logging
from .otel import init_otel, shutdown_otel
from .sentry import init_sentry, shutdown_sentry
from ..config.telemetry import SENTRY_DSN, AXIOM_API_TOKEN

logger = logging.getLogger(__name__)


def init_telemetry() -> None:
    """Activate configured telemetry backends. Idempotent."""
    if AXIOM_API_TOKEN:
        init_otel()
    else:
        logger.info("Axiom/OTel disabled (AXIOM_API_TOKEN not set)")

    if SENTRY_DSN:
        init_sentry()
    else:
        logger.info("Sentry disabled (SENTRY_DSN not set)")


def shutdown_telemetry() -> None:
    """Flush and shutdown all telemetry backends. Idempotent."""
    shutdown_sentry()
    shutdown_otel()


__all__ = ["init_telemetry", "shutdown_telemetry"]
