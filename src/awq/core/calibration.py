"""Calibration utilities for AWQ quantization."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CalibrationConfig:
    """Configuration for AWQ calibration."""
    dataset: str = "pileval"
    nsamples: int = 64
    seqlen: int = 2048
    w_bit: int = 4
    q_group_size: int = 128
    zero_point: bool = True
    version: str = "GEMM"


def prepare_tokenizer_for_calibration(tokenizer: Any, target_seqlen: int) -> None:
    """Prepare tokenizer for calibration with the given sequence length.

    AutoAWQ's calibration pipeline occasionally batches very long samples from the
    chosen dataset. When the tokenizer (or underlying model config) reports a
    smaller `model_max_length`, Hugging Face emits noisy warnings like
    "Token indices sequence length is longer than the specified maximum…" even
    though we truncate before feeding the model. To quiet that noise and keep the
    pipeline calm, we inflate the tokenizer's advertised limits while preserving
    the original value so downstream code can restore it if needed.
    """

    # We allow arbitrarily long samples for calibration; clamp inside the model path
    max_len_target = max(int(target_seqlen), 1_000_000)

    def _maybe_set_attr(obj: Any, attr: str, value: int) -> None:
        if not hasattr(obj, attr):
            try:
                setattr(obj, attr, value)
            except Exception:
                pass
            return

        try:
            current = getattr(obj, attr)
        except Exception:
            current = None

        try:
            if isinstance(current, int) and current > 0:
                if current < value:
                    setattr(obj, attr, value)
            else:
                setattr(obj, attr, value)
        except Exception:
            pass

    if hasattr(tokenizer, "model_max_length"):
        original_max_length = getattr(tokenizer, "_original_max_length", None)
        if original_max_length is None:
            tokenizer._original_max_length = tokenizer.model_max_length
        _maybe_set_attr(tokenizer, "model_max_length", max_len_target)

    init_kwargs = getattr(tokenizer, "init_kwargs", None)
    if isinstance(init_kwargs, dict):
        for key in ("model_max_length", "max_length", "max_position_embeddings"):
            current = init_kwargs.get(key)
            if not isinstance(current, int) or current <= 0 or current < max_len_target:
                init_kwargs[key] = max_len_target

    for attr in (
        "max_len_single_sentence",
        "max_len_sentences_pair",
        "max_length",
        "n_positions",
    ):
        _maybe_set_attr(tokenizer, attr, max_len_target)
