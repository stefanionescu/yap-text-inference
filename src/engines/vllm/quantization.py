"""Quantization metadata helpers for vLLM engine configuration."""

from __future__ import annotations

import os
from typing import Any

from src.helpers.models import _is_local_model_path
from src.utils.io import read_json_file

__all__ = [
    "detect_quantization_backend",
    "log_detected_quantization",
    "resolve_model_origin",
]

_QUANT_CONFIG_CANDIDATES = (
    "config.json",
    "quantization_config.json",
    "quant_config.json",
    "awq_config.json",
)
_AWQ_METADATA_FILE = "awq_metadata.json"


def detect_quantization_backend(model_path: str) -> tuple[str | None, dict[str, Any]]:
    """Attempt both local and remote detection for llmcompressor exports."""
    method, payload = _detect_local_quantization_backend(model_path)
    if method:
        return method, payload
    return _detect_remote_quantization_backend(model_path)


def log_detected_quantization(model_path: str, method: str, payload: dict[str, Any]) -> None:
    """Emit a concise description of the quantization metadata."""
    quant_cfg = _extract_quant_config(payload)
    w_bit = quant_cfg.get("w_bit")
    q_group = quant_cfg.get("q_group_size")
    scheme = quant_cfg.get("scheme")
    zero_point = quant_cfg.get("zero_point")
    version = quant_cfg.get("version")

    details = []
    if scheme:
        details.append(f"scheme={scheme}")
    if w_bit is not None:
        details.append(f"w_bit={w_bit}")
    if q_group is not None:
        details.append(f"q_group_size={q_group}")
    if zero_point is not None:
        zero_status = "enabled" if bool(zero_point) else "disabled"
        details.append(f"zero_point={zero_status}")
    if version:
        details.append(f"awq_version={version}")

    detail_str = ", ".join(details) if details else "no metadata found"
    print(f"[config] Detected {method} quantization for {model_path}: {detail_str}")


def resolve_model_origin(model_path: str) -> str:
    """Best effort to determine the underlying HF repo for local AWQ exports."""
    if not model_path:
        return ""
    if _is_local_model_path(model_path):
        meta_path = os.path.join(model_path, _AWQ_METADATA_FILE)
        payload = read_json_file(meta_path)
        if isinstance(payload, dict):
            source = payload.get("source_model")
            if isinstance(source, str) and source.strip():
                return source.strip()
    return model_path


def _detect_local_quantization_backend(model_path: str) -> tuple[str | None, dict[str, Any]]:
    """Inspect local model files to detect the quantization backend."""
    if not _is_local_model_path(model_path):
        return None, {}

    for filename in _QUANT_CONFIG_CANDIDATES:
        candidate = os.path.join(model_path, filename)
        if not os.path.isfile(candidate):
            continue
        payload = read_json_file(candidate)
        if payload is None:
            continue
        quant_method = _extract_quantization_method(payload)
        if quant_method:
            return quant_method, payload if isinstance(payload, dict) else {}
    return None, {}


def _detect_remote_quantization_backend(model_path: str) -> tuple[str | None, dict[str, Any]]:
    """Inspect remote Hugging Face repos for quantization metadata."""
    if not model_path or "/" not in model_path or _is_local_model_path(model_path):
        return None, {}
    try:
        from huggingface_hub import hf_hub_download
    except Exception as exc:
        print(f"[config] Warning: huggingface_hub not available for remote quantization detection ({exc})")
        return None, {}

    token = os.getenv("HUGGINGFACE_HUB_TOKEN") or os.getenv("HF_TOKEN")
    cache_dir = os.getenv("HF_HOME")

    for filename in _QUANT_CONFIG_CANDIDATES:
        try:
            downloaded = hf_hub_download(
                repo_id=model_path,
                filename=filename,
                token=token,
                cache_dir=cache_dir,
                local_files_only=False,
                resume_download=True,
            )
        except Exception:
            continue
        payload = read_json_file(downloaded)
        if payload is None:
            continue
        quant_method = _extract_quantization_method(payload)
        if quant_method:
            return quant_method, payload
    return None, {}


def _extract_quant_config(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    config = payload.get("quantization_config")
    if isinstance(config, dict):
        return config
    return payload if isinstance(payload, dict) else {}


def _extract_quantization_method(payload: Any) -> str | None:
    """Extract the declared quantization method from a config payload."""
    if not isinstance(payload, dict):
        return None

    def _from_dict(data: dict[str, Any]) -> str | None:
        for key in ("quantization_method", "quant_method", "quantization"):
            value = data.get(key)
            if isinstance(value, str):
                normalized = _normalize_quantization_name(value)
                if normalized:
                    return normalized
        return None

    direct = _from_dict(payload)
    if direct:
        return direct

    nested = payload.get("quantization_config")
    if isinstance(nested, dict):
        nested_value = _from_dict(nested)
        if nested_value:
            return nested_value
        return _normalize_quantization_name(nested.get("quantization_method")) or "compressed-tensors"

    return None


def _normalize_quantization_name(name: str | None) -> str | None:
    """Normalize various quantization labels to vLLM's expected names."""
    if not name:
        return None
    normalized = name.strip().lower().replace("_", "-")
    mapping = {
        "awq": "awq_marlin",
        "awq-marlin": "awq_marlin",
        "compressed-tensors": "compressed-tensors",
        "compressedtensors": "compressed-tensors",
        "compressed_tensors": "compressed-tensors",
        "compressed-tensor": "compressed-tensors",
        "nvfp4": "compressed-tensors",
        "autoround": "compressed-tensors",
    }
    return mapping.get(normalized)

