"""Classifier package for screenshot intent detection.

This package provides a lightweight BERT-style classifier for detecting
when users want to take a screenshot. It's much faster than running
the full chat model for intent detection.

Architecture:
    ClassifierToolAdapter:
        High-level interface that handles:
        - Input formatting (combining history + current utterance)
        - Threshold-based decision (probability -> yes/no)
        - GPU memory limit enforcement

    TorchClassifierBackend:
        PyTorch inference backend supporting:
        - BERT-style models (DistilBERT, RoBERTa, etc.)
        - Longformer models (for longer context)
        - Optional torch.compile() optimization

    BatchExecutor:
        Micro-batching for efficiency:
        - Accumulates requests for batch_max_delay_ms
        - Runs batches up to batch_max_size
        - Thread-based for non-blocking operation

Configuration (via environment):
    TOOL_MODEL: HuggingFace model path/ID
    TOOL_DECISION_THRESHOLD: Probability threshold (default 0.66)
    TOOL_COMPILE: Whether to use torch.compile()
    TOOL_MAX_LENGTH: Maximum input tokens
    TOOL_MICROBATCH_MAX_SIZE: Max requests per batch
    TOOL_MICROBATCH_MAX_DELAY_MS: Max wait time for batch

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
        )
        from src.config.timeouts import TOOL_TIMEOUT_S
        
        _classifier_adapter = ClassifierToolAdapter(
            model_path=TOOL_MODEL,
            threshold=TOOL_DECISION_THRESHOLD,
            compile_model=TOOL_COMPILE,
            max_length=TOOL_MAX_LENGTH,
            batch_max_size=TOOL_MICROBATCH_MAX_SIZE,
            batch_max_delay_ms=TOOL_MICROBATCH_MAX_DELAY_MS,
            request_timeout_s=TOOL_TIMEOUT_S,
            gpu_memory_frac=TOOL_GPU_FRAC,
        )
    
    return _classifier_adapter


def reset_classifier_adapter() -> None:
    """Reset the global classifier adapter (for testing)."""
    global _classifier_adapter
    _classifier_adapter = None


__all__ = [
    "ClassifierToolAdapter",
    "get_classifier_adapter",
    "reset_classifier_adapter",
]
