"""Transformers library log suppression.

Configures transformers logging verbosity and progress bars.
This is separate from the monkey-patches in src/scripts/patches.py.
"""

from __future__ import annotations

import logging
import os

__all__ = ["configure_transformers_logging"]

logger = logging.getLogger("log_filter")


def configure_transformers_logging() -> None:
    """Quiet transformers logging/progress bars if the library is installed."""
    try:
        from transformers.utils import logging as transformers_logging
    except ModuleNotFoundError:
        return

    try:
        transformers_logging.set_verbosity_warning()
    except Exception as exc:  # pragma: no cover
        logger.debug("failed to set transformers verbosity: %s", exc)

    try:
        transformers_logging.disable_progress_bar()
    except Exception as exc:  # pragma: no cover
        logger.debug("failed to disable transformers progress: %s", exc)

    os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

