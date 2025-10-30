"""Application logging configuration values."""

import os


APP_LOG_LEVEL = (os.getenv("APP_LOG_LEVEL", "INFO") or "INFO").upper()
APP_LOG_FORMAT = os.getenv(
    "APP_LOG_FORMAT",
    "%(levelname)s %(asctime)s [%(name)s:%(lineno)d] %(message)s",
)


__all__ = [
    "APP_LOG_LEVEL",
    "APP_LOG_FORMAT",
]


