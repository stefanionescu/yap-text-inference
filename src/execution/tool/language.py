"""Language detection utilities for filtering non-English messages."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def create_language_detector() -> Any | None:
    """Create a lingua language detector.

    Runtime bootstrap is responsible for constructing this eagerly when the
    tool pipeline is enabled.
    """
    try:
        from lingua import LanguageDetectorBuilder  # noqa: PLC0415
    except ImportError:
        logger.debug("lingua not available - language detection disabled")
        return None
    return LanguageDetectorBuilder.from_all_languages().with_preloaded_language_models().build()


def is_mostly_english(text: str, detector: Any | None) -> bool:
    """Check if text is mostly in English.

    If the detector is unavailable, returns True (fail-open) to avoid blocking
    requests due to optional dependency issues.
    """
    if not text or not text.strip():
        return True
    if detector is None:
        return True

    normalized = text.strip()
    try:
        from lingua import Language  # noqa: PLC0415

        detected = detector.detect_language_of(normalized)
        is_english = detected == Language.ENGLISH
        if not is_english:
            lang_name = detected.name if detected else "UNKNOWN"
            logger.debug("language_filter: detected=%s text=%r", lang_name, normalized[:100])
        return is_english
    except Exception as exc:  # noqa: BLE001
        logger.warning("language_filter: error=%s", exc)
        return True


__all__ = ["create_language_detector", "is_mostly_english"]
