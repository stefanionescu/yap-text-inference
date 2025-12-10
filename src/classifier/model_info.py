"""Model metadata helpers for the classifier adapter."""

from __future__ import annotations

from dataclasses import dataclass

from transformers import AutoConfig  # type: ignore[import]


@dataclass(slots=True)
class ClassifierModelInfo:
    """Metadata describing the classifier checkpoint + runtime needs."""
    model_id: str
    model_type: str  # "bert" or "longformer"
    max_length: int
    num_labels: int


def build_model_info(model_path: str, max_length: int) -> ClassifierModelInfo:
    """Inspect the Hugging Face config and produce classifier metadata."""
    config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
    model_type = (
        "longformer"
        if getattr(config, "model_type", "").lower() == "longformer"
        else "bert"
    )
    num_labels = int(getattr(config, "num_labels", 2))
    return ClassifierModelInfo(
        model_id=model_path,
        model_type=model_type,
        max_length=max_length,
        num_labels=num_labels,
    )


__all__ = ["ClassifierModelInfo", "build_model_info"]
