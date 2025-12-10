"""Classifier package for screenshot intent detection.

This package provides a lightweight classifier-based alternative to
autoregressive LLMs for tool call detection. The classifier determines
whether a screenshot should be taken based on user utterances.

Usage:
    from src.classifier import get_classifier_adapter
    
    adapter = get_classifier_adapter()
    user_history = session_handler.get_user_history_text(session_id)
    result = adapter.run_tool_inference(user_utt, user_history)
"""

from __future__ import annotations

from .adapter import ClassifierToolAdapter

# Global instance
_classifier_adapter: ClassifierToolAdapter | None = None


def get_classifier_adapter() -> ClassifierToolAdapter:
    """Get the global classifier adapter instance.
    
    Lazily initializes the classifier using config values from environment.
    """
    global _classifier_adapter
    
    if _classifier_adapter is None:
        from src.config import (
            TOOL_MODEL,
            CLASSIFIER_THRESHOLD,
            CLASSIFIER_COMPILE,
            CLASSIFIER_HISTORY_TOKENS,
        )
        
        _classifier_adapter = ClassifierToolAdapter(
            model_path=TOOL_MODEL,
            threshold=CLASSIFIER_THRESHOLD,
            history_max_tokens=CLASSIFIER_HISTORY_TOKENS,
            compile_model=CLASSIFIER_COMPILE,
        )
    
    return _classifier_adapter


def reset_classifier_adapter() -> None:
    """Reset the global classifier adapter (for testing)."""
    global _classifier_adapter
    _classifier_adapter = None
    ClassifierToolAdapter.reset_instance()


__all__ = [
    "ClassifierToolAdapter",
    "get_classifier_adapter",
    "reset_classifier_adapter",
]
