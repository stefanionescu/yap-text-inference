"""Language detection utilities for filtering non-English messages."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Lazy initialization - only import lingua when actually needed
# This allows the module to be imported even if lingua isn't installed yet
_STATE = {"detector": None}


def _get_detector():
    """Lazy initialization of the language detector."""
    detector = _STATE["detector"]
    if detector is None:
        try:
            from lingua import LanguageDetectorBuilder  # noqa: PLC0415

            # Build detector once - only load English vs all others
            # This is faster and sufficient for our use case (is it English or not?)
            detector = LanguageDetectorBuilder.from_all_languages().with_preloaded_language_models().build()
        except ImportError:
            # lingua not installed - return None to indicate unavailable
            logger.debug("lingua not available - language detection disabled")
            detector = False  # Use False as sentinel to avoid retrying
        _STATE["detector"] = detector
    return detector if detector is not False else None


def is_mostly_english(text: str) -> bool:
    """Check if text is mostly in English.

    Uses lingua for accurate language detection, including short texts.
    If lingua is not available, always returns True (fail-open).

    Args:
        text: The text to check

    Returns:
        True if the text is detected as English or if detection fails
        (fail-open to avoid blocking valid requests)
    """
    if not text or not text.strip():
        return True  # Empty text is fine

    detector = _get_detector()
    if detector is None:
        # lingua not available - fail open
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
    except Exception as e:
        # Unexpected error - fail open to avoid blocking requests
        logger.warning("language_filter: error=%s", e)
        return True


__all__ = ["is_mostly_english"]
