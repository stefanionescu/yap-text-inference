"""Application logging configuration values and helpers."""

import os
import logging
import contextlib

APP_LOG_LEVEL = (os.getenv("APP_LOG_LEVEL", "INFO") or "INFO").upper()
APP_LOG_FORMAT = os.getenv(
    "APP_LOG_FORMAT",
    "%(levelname)s %(asctime)s [%(name)s:%(lineno)d] %(message)s",
)

# Log labels for stream types
CHAT_STREAM_LABEL = "chat"


def configure_logging() -> None:
    """Initialize root logging configuration once per process."""
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=APP_LOG_LEVEL, format=APP_LOG_FORMAT)
    else:
        root_logger.setLevel(APP_LOG_LEVEL)
        for handler in root_logger.handlers:
            with contextlib.suppress(Exception):
                handler.setLevel(APP_LOG_LEVEL)

    logging.getLogger("src").setLevel(APP_LOG_LEVEL)


__all__ = [
    "APP_LOG_LEVEL",
    "APP_LOG_FORMAT",
    "CHAT_STREAM_LABEL",
    "configure_logging",
]


