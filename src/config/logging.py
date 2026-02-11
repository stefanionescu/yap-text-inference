"""Application logging configuration values and helpers."""

import os
import logging
import contextlib

from src.logging import install_log_context

APP_LOG_LEVEL = (os.getenv("APP_LOG_LEVEL") or "INFO").upper()
APP_LOG_FORMAT = os.getenv(
    "APP_LOG_FORMAT",
    "%(levelname)s %(asctime)s name=%(name)s session_id=%(session_id)s "
    "request_id=%(request_id)s client_id=%(client_id)s msg=%(message)s",
)
APP_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

# Log labels for stream types
CHAT_STREAM_LABEL = "chat"


def configure_logging() -> None:
    """Initialize root logging configuration once per process."""
    install_log_context()
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=APP_LOG_LEVEL, format=APP_LOG_FORMAT, datefmt=APP_LOG_DATEFMT)
    else:
        root_logger.setLevel(APP_LOG_LEVEL)
        for handler in root_logger.handlers:
            with contextlib.suppress(Exception):
                handler.setLevel(APP_LOG_LEVEL)
                handler.setFormatter(logging.Formatter(APP_LOG_FORMAT, datefmt=APP_LOG_DATEFMT))

    logging.getLogger("src").setLevel(APP_LOG_LEVEL)


__all__ = [
    "APP_LOG_LEVEL",
    "APP_LOG_FORMAT",
    "APP_LOG_DATEFMT",
    "CHAT_STREAM_LABEL",
    "configure_logging",
]
