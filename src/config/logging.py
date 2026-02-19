"""Application logging configuration values."""

import os

APP_LOG_LEVEL = (os.getenv("APP_LOG_LEVEL") or "INFO").upper()
APP_LOG_FORMAT = os.getenv(
    "APP_LOG_FORMAT",
    "%(levelname)s %(asctime)s name=%(name)s session_id=%(session_id)s "
    "request_id=%(request_id)s client_id=%(client_id)s msg=%(message)s",
)
APP_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

# Log labels for stream types
CHAT_STREAM_LABEL = "chat"


__all__ = [
    "APP_LOG_LEVEL",
    "APP_LOG_FORMAT",
    "APP_LOG_DATEFMT",
    "CHAT_STREAM_LABEL",
]
