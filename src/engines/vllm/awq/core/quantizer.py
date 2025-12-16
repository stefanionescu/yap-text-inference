"""Core AWQ quantization logic (llmcompressor + AutoAWQ fallback)."""

from __future__ import annotations

import os
from typing import Any

from src.helpers.awq import resolve_total_len, TotalLengthPolicy
from src.config.limits import CHAT_MAX_LEN, CHAT_MAX_OUT
from ..utils import resolve_calibration_seqlen, is_awq_dir
from ..utils.model_utils import (
    is_moe_model,
    load_model_config,
    prefetch_model,
    requires_autoawq_backend,
)
from .backends import quantize_with_autoawq, quantize_with_llmcompressor
from .calibration import CalibrationConfig


def _is_classifier_model_path(model_path: str) -> bool:
    """Check if model path refers to a classifier model."""
    # Import here to avoid circular imports
    from src.helpers.models import is_classifier_model
    return is_classifier_model(model_path)


CHAT_TOTAL_POLICY = TotalLengthPolicy(
    kind="chat",
    default_total=CHAT_MAX_LEN + CHAT_MAX_OUT,
    len_env="CHAT_MAX_LEN",
    out_env="CHAT_MAX_OUT",
)


def compute_chat_calibration_seqlen(requested: int) -> int:
    return resolve_total_len(requested, CHAT_TOTAL_POLICY)


class AWQQuantizer:
    """AWQ quantization manager backed by llmcompressor."""
    
    def __init__(self, config: CalibrationConfig):
        self.config = config
        
    def quantize_model(
        self,
        model_path: str,
        output_dir: str,
        force: bool = False,
    ) -> bool:
        """Quantize a model using llmcompressor or AutoAWQ (for Qwen).
        
        Raises ValueError if model is a classifier (not supported).
        """
        # Block classifier models from quantization
        if _is_classifier_model_path(model_path):
            raise ValueError(
                f"Cannot quantize classifier model '{model_path}'. "
                "Classifier models use transformers AutoModelForSequenceClassification, "
                "not autoregressive LLMs. They don't support AWQ quantization."
            )

        if not force and is_awq_dir(output_dir):
            print(f"[awq] Using existing quantized model at {output_dir}")
            return True

        os.makedirs(output_dir, exist_ok=True)

        quant_config: dict[str, Any] = {
            "scheme": f"W{self.config.w_bit}A16",
            "zero_point": self.config.zero_point,
            "q_group_size": self.config.q_group_size,
            "w_bit": self.config.w_bit,
            "version": self.config.version,
            "targets": "Linear",
            "ignore": ["lm_head"],
        }

        resolved_model_path = prefetch_model(model_path)
        if resolved_model_path is None:
            return False

        model_config = load_model_config(resolved_model_path)
        hf_model_type = getattr(model_config, "model_type", "") if model_config is not None else ""
        
        # Block MoE models - AWQ quantization doesn't support expert layers
        if is_moe_model(model_config, model_path):
            raise ValueError(
                f"Cannot quantize MoE model '{model_path}'. "
                "Mixture of Experts (MoE) models use sparse expert layers (mlp.experts.*) "
                "that are not supported by AWQ quantization. "
                "Consider using a pre-quantized version (e.g., GGUF/GGML) or a dense model instead."
            )
        
        requires_autoawq = requires_autoawq_backend(model_config, model_path)

        requested_seqlen = compute_chat_calibration_seqlen(self.config.seqlen)
        target_seqlen = resolve_calibration_seqlen(requested_seqlen, model_config)
        calibration_kind = "Chat"
        if target_seqlen != requested_seqlen:
            print(f"[awq] {calibration_kind} model calibration seqlen adjusted to {target_seqlen}")
        else:
            print(f"[awq] {calibration_kind} model calibration seqlen = {target_seqlen}")

        if requires_autoawq:
            return quantize_with_autoawq(
                model_path=model_path,
                resolved_model_path=resolved_model_path,
                output_dir=output_dir,
                quant_config=quant_config,
                target_seqlen=target_seqlen,
            )

        return quantize_with_llmcompressor(
            calibration_config=self.config,
            model_path=model_path,
            resolved_model_path=resolved_model_path,
            output_dir=output_dir,
            quant_config=quant_config,
            target_seqlen=target_seqlen,
            hf_model_type=hf_model_type,
            calibration_kind=calibration_kind,
        )
