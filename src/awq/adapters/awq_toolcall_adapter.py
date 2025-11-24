#!/usr/bin/env python3
"""Toolcall-specific helpers for AWQ quantization."""

from __future__ import annotations

from src.config.awq import (
    TOOL_TOTAL_POLICY,
    TOOLCALL_MODEL_MARKERS,
    normalize_model_id,
    resolve_total_len,
)


def is_toolcall_model(model_id: str) -> bool:
    norm = normalize_model_id(model_id)
    return any(marker in norm for marker in TOOLCALL_MODEL_MARKERS)


def compute_toolcall_calibration_seqlen(requested: int) -> int:
    """Return the calibration sequence length floor for toolcall models."""
    return resolve_total_len(requested, TOOL_TOTAL_POLICY)


def apply_awq_compatibility_patches() -> None:
    """Ensure common AWQ patches are applied for all models."""
    _apply_toolcall_qwen_patch()


def _apply_toolcall_qwen_patch() -> None:
    try:
        from transformers.models.qwen2.modeling_qwen2 import Qwen2Model  # type: ignore
    except Exception as exc:
        print(f"[awq] Toolcall patch skipped: unable to import Qwen2Model ({exc})")
        return

    if getattr(Qwen2Model, "_toolcall_attention_type_patch", False):
        return

    original_forward = Qwen2Model.forward

    def patched_forward(self, *args, **kwargs):  # type: ignore[override]
        try:
            layer_types = getattr(self.config, "layer_types", None)
            if layer_types is not None:
                for idx, decoder_layer in enumerate(self.layers[: self.config.num_hidden_layers]):
                    if hasattr(decoder_layer, "attention_type"):
                        continue
                    try:
                        attention_type = layer_types[idx]
                    except Exception:
                        attention_type = "full_attention"
                    decoder_layer.attention_type = attention_type
        except Exception:
            pass
        return original_forward(self, *args, **kwargs)

    Qwen2Model.forward = patched_forward  # type: ignore[assignment]
    Qwen2Model._toolcall_attention_type_patch = True
    print("[awq] Applied Toolcall-specific Qwen2 attention patch")


__all__ = [
    "apply_awq_compatibility_patches",
    "compute_toolcall_calibration_seqlen",
    "is_toolcall_model",
]


