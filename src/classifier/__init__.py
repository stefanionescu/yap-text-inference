"""Classifier package for screenshot intent detection.

This package provides a lightweight classifier for detecting when users
want to take a screenshot. Supports BERT-style and Longformer models.

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
from .factory import get_classifier_adapter, reset_classifier_adapter

__all__ = [
    "ClassifierToolAdapter",
    "get_classifier_adapter",
    "reset_classifier_adapter",
]
