"""Model-related utilities for AWQ quantization."""

from __future__ import annotations

import os
import re
import time
from typing import Any
from src.config.limits import DOWNLOAD_MAX_RETRIES, DOWNLOAD_BACKOFF_MAX_SECONDS


def is_awq_dir(path: str) -> bool:
    """Check if a directory contains a valid AWQ quantized model.

    Looks for typical AWQ model artifacts:
    - config.json
    - model safetensors files
    - awq_metadata.json (written by our quantizer)
    """
    if not path or not os.path.isdir(path):
        return False

    config_path = os.path.join(path, "config.json")
    if not os.path.isfile(config_path):
        return False

    # Check for model weights (safetensors or bin)
    has_weights = any(
        f.endswith((".safetensors", ".bin")) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))
    )

    return has_weights


def resolve_calibration_seqlen(requested: int, model_or_config: Any | None) -> int:
    """Resolve the calibration sequence length based on model or config metadata."""
    requested = max(int(requested), 1)

    config = (
        getattr(model_or_config, "config", None)
        if model_or_config is not None and hasattr(model_or_config, "config")
        else model_or_config
    )

    max_positions = None
    if config is not None:
        candidates: list[int] = []
        for attr in ("max_position_embeddings", "max_sequence_length"):
            value = getattr(config, attr, None)
            if value is not None:
                candidates.append(int(value))
        if candidates:
            max_positions = max(candidates)

    if max_positions is not None and requested > max_positions:
        print(f"[awq] Requested calibration seqlen {requested} exceeds model limit {max_positions}; clamping.")
        return max_positions

    return requested


def is_moe_model(model_config: Any | None, model_identifier: str) -> bool:
    """Return True when this model is a Mixture of Experts (MoE) model.

    MoE models have sparse architectures with expert layers that are not
    supported by AWQ quantization.
    """
    # Check config for MoE indicators
    if model_config is not None:
        # Standard MoE config attributes
        num_experts = getattr(model_config, "num_local_experts", None)
        if num_experts is None:
            num_experts = getattr(model_config, "num_experts", None)
        if num_experts is not None and int(num_experts) > 1:
            return True

        # Some models use 'moe' in their model_type
        model_type = (getattr(model_config, "model_type", "") or "").lower()
        if "moe" in model_type:
            return True

    # Fallback: detect MoE from model identifier patterns
    # Common patterns: "-A3B", "MoE", "Mixtral", etc.
    from src.helpers.profiles import normalize_model_id  # noqa: PLC0415

    normalized = normalize_model_id(model_identifier)

    # Qwen3 MoE naming convention: "qwen3-30b-a3b" (30B total, 3B active)
    # The "-aXb" suffix indicates active parameters in MoE
    if re.search(r"-a\d+b", normalized):
        return True

    moe_markers = ("moe", "mixtral")
    return any(marker in normalized for marker in moe_markers)


def prefetch_model(model_path: str) -> str | None:
    """Resolve remote HF repos to a local snapshot for robustness."""

    resolved_model_path = model_path
    if os.path.isdir(model_path) or "/" not in model_path:
        return resolved_model_path

    try:
        from huggingface_hub import snapshot_download  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Failed to import huggingface_hub for snapshot download: {exc}")
        return None

    token = os.environ.get("HF_TOKEN")
    cache_dir = os.environ.get("HF_HOME")

    print("[awq] Fetching model from Hub...")
    last_err: Exception | None = None
    for attempt in range(1, DOWNLOAD_MAX_RETRIES + 1):
        try:
            resolved_model_path = snapshot_download(
                repo_id=model_path,
                token=token,
                local_files_only=False,
                cache_dir=cache_dir,
            )
            last_err = None
            break
        except Exception as dl_err:  # noqa: BLE001
            last_err = dl_err
            backoff = min(2**attempt, DOWNLOAD_BACKOFF_MAX_SECONDS)
            print(f"[awq] Hub download failed (attempt {attempt}/{DOWNLOAD_MAX_RETRIES}): {dl_err}")
            if attempt < DOWNLOAD_MAX_RETRIES:
                print(f"[awq] Retrying in {backoff}s…")
                time.sleep(backoff)

    if last_err is not None:
        print(
            "[awq] Quantization failed: could not download model from Hugging Face. "
            "Check network access, repository visibility, and set HF_TOKEN if needed."
        )
        return None

    return resolved_model_path


def load_model_config(model_path: str) -> Any | None:
    """Best-effort load of model config for seqlen validation."""

    try:
        from transformers import AutoConfig  # noqa: PLC0415
    except Exception:
        return None

    try:
        return AutoConfig.from_pretrained(model_path, trust_remote_code=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Warning: unable to load config for {model_path}: {exc}")
        return None
