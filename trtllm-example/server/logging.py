"""Logging configuration and filters."""

import logging


class SuppressWsConnectionLogs(logging.Filter):
    """Filter out repetitive uvicorn WebSocket connection open/close messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return msg not in ("connection open", "connection closed")


def configure_logging() -> None:
    """Apply logging filters to suppress noisy logs."""
    logging.getLogger("uvicorn.error").addFilter(SuppressWsConnectionLogs())
