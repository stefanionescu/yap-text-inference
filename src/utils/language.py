"""Language detection utilities for filtering non-English messages."""

from __future__ import annotations

import logging

from lingua import Language, LanguageDetectorBuilder

logger = logging.getLogger(__name__)

# Build detector once at module load - only load English vs all others
# This is faster and sufficient for our use case (is it English or not?)
_detector = (
    LanguageDetectorBuilder
    .from_all_languages()
    .with_preloaded_language_models()
    .build()
)


def is_mostly_english(text: str) -> bool:
    """Check if text is mostly in English.
    
    Uses lingua for accurate language detection, including short texts.
    
    Args:
        text: The text to check
        
    Returns:
        True if the text is detected as English or if detection fails
        (fail-open to avoid blocking valid requests)
    """
    if not text or not text.strip():
        return True  # Empty text is fine
    
    normalized = text.strip()
    
    try:
        detected = _detector.detect_language_of(normalized)
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
