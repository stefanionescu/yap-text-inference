import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSettings:
    """Model and tokenizer configuration."""

    # Allow switching base model via MODEL_PRESET when MODEL_ID is not explicitly set
    _preset = os.getenv("MODEL_PRESET", "canopy").strip().lower()
    _default_model = "yapwithai/fast-orpheus-3b-0.1-ft" if _preset == "fast" else "yapwithai/canopy-orpheus-3b-0.1-ft"
    model_id: str = os.getenv("MODEL_ID", _default_model)
    hf_token: str | None = os.environ.get("HF_TOKEN")
