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
            TOOL_GPU_FRAC,
            TOOL_DECISION_THRESHOLD,
            TOOL_COMPILE,
            TOOL_MAX_LENGTH,
            TOOL_MICROBATCH_MAX_SIZE,
            TOOL_MICROBATCH_MAX_DELAY_MS,
            TOOL_USE_ONNX,
            TOOL_ONNX_DIR,
            TOOL_ONNX_OPSET,
        )
        from src.config.timeouts import TOOL_TIMEOUT_S
        
        _classifier_adapter = ClassifierToolAdapter(
            model_path=TOOL_MODEL,
            threshold=TOOL_DECISION_THRESHOLD,
            compile_model=TOOL_COMPILE,
            max_length=TOOL_MAX_LENGTH,
            microbatch_max_size=TOOL_MICROBATCH_MAX_SIZE,
            microbatch_max_delay_ms=TOOL_MICROBATCH_MAX_DELAY_MS,
            request_timeout_s=TOOL_TIMEOUT_S,
            use_onnx=TOOL_USE_ONNX,
            onnx_dir=TOOL_ONNX_DIR,
            onnx_opset=TOOL_ONNX_OPSET,
            gpu_memory_frac=TOOL_GPU_FRAC,
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
