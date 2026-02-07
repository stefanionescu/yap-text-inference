"""Model metadata helpers for the classifier adapter.

This module provides utilities for extracting metadata from HuggingFace
model configurations. The metadata is used to:

1. Determine model type (BERT-style vs Longformer)
2. Configure sequence length limits
3. Set up the correct inference path

ClassifierModelInfo:
    Dataclass holding model metadata extracted from config.json

build_model_info():
    Factory function that reads HuggingFace config and builds metadata.
"""

from __future__ import annotations

from transformers import AutoConfig  # type: ignore[import]

from src.state import ClassifierModelInfo


def build_model_info(model_path: str, max_length: int) -> ClassifierModelInfo:
    """Inspect the Hugging Face config and produce classifier metadata.

    Reads config.json from the model path/repo to determine:
    - Model type (BERT vs Longformer)
    - Number of classification labels

    Args:
        model_path: HuggingFace model ID or local directory path.
        max_length: User-configured maximum sequence length.

    Returns:
        ClassifierModelInfo with extracted/configured metadata.
    """
    config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
    config_type = getattr(config, "model_type", "").lower()
    model_type = "longformer" if config_type == "longformer" else "bert"
    num_labels = int(getattr(config, "num_labels", 2))
    return ClassifierModelInfo(
        model_id=model_path,
        model_type=model_type,
        max_length=max_length,
        num_labels=num_labels,
    )


__all__ = ["build_model_info"]
