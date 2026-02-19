"""Quantization metadata helpers for vLLM engine configuration.

This module provides utilities for:
1. Sanitization: Removing unsupported dtype fields from quant configs
2. Detection: Finding and parsing quantization metadata from local/remote models
3. Resolution: Mapping quantization method names to vLLM backends

The functions are organized in logical sections:
- Sanitization (strip unsupported fields from configs)
- Detection (find quant backend from local or HF models)
- Resolution (resolve model origins and log metadata)
"""

from __future__ import annotations

import os
import stat
import logging
import contextlib
from typing import Any
from collections.abc import Callable

from src.helpers.models import is_local_model_path
from src.config.quantization import QUANT_NAME_MAPPING
from src.helpers.io import read_json_file, write_json_file
from src.config import AWQ_METADATA_FILENAME, QUANT_CONFIG_FILENAMES, UNSUPPORTED_QUANT_DTYPE_FIELDS

logger = logging.getLogger(__name__)

# ============================================================================
# Private helpers
# ============================================================================


def _sanitize_local_configs(model_path: str) -> None:
    """Sanitize quantization config files in a local directory."""
    for filename in QUANT_CONFIG_FILENAMES:
        candidate = os.path.join(model_path, filename)
        if os.path.isfile(candidate):
            _sanitize_config_file(candidate)


def _sanitize_remote_configs(model_path: str) -> None:
    """Sanitize quantization config files from a remote HuggingFace repo."""
    download_fn = _get_hf_download_fn()
    if download_fn is None:
        return

    for filename in QUANT_CONFIG_FILENAMES:
        downloaded = download_fn(model_path, filename)
        if downloaded:
            _sanitize_config_file(downloaded)


def _sanitize_config_file(path: str) -> None:
    """Sanitize a single JSON config file by removing unsupported fields."""
    payload = read_json_file(path)
    if payload is None:
        return
    if not strip_unsupported_fields(payload):
        return

    # HF cache blobs are often read-only; try to make writable before writing
    original_mode = None
    with contextlib.suppress(OSError):
        file_stat = os.stat(path)
        if not (file_stat.st_mode & stat.S_IWUSR):
            original_mode = file_stat.st_mode
            os.chmod(path, file_stat.st_mode | stat.S_IWUSR)

    success = write_json_file(path, payload)

    # Restore original permissions if we changed them
    if original_mode is not None:
        with contextlib.suppress(OSError):
            os.chmod(path, original_mode)

    if success:
        logger.info(
            "[config] Sanitized quantization metadata for %s: removed %s",
            path,
            ", ".join(UNSUPPORTED_QUANT_DTYPE_FIELDS),
        )
    else:
        logger.warning("[config] Failed to sanitize quantization metadata at %s", path)


def _get_hf_download_fn() -> Callable[[str, str], str | None] | None:
    """Return a function to download files from HuggingFace, or None if unavailable."""
    try:
        from huggingface_hub import hf_hub_download  # noqa: PLC0415
    except Exception as exc:
        logger.warning("[config] huggingface_hub not available: %s", exc)
        return None

    token = os.getenv("HF_TOKEN")
    cache_dir = os.getenv("HF_HOME")

    def download(repo_id: str, filename: str) -> str | None:
        try:
            return hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                token=token,
                cache_dir=cache_dir,
                local_files_only=False,
            )
        except Exception:
            return None

    return download


def _detect_from_configs(
    file_resolver: Callable[[str], str | None],
) -> tuple[str | None, dict[str, Any]]:
    """Detect quantization method from config files using a resolver function."""
    for filename in QUANT_CONFIG_FILENAMES:
        path = file_resolver(filename)
        if not path:
            continue
        payload = read_json_file(path)
        if payload is None:
            continue
        quant_method = _extract_quant_method(payload)
        if quant_method:
            return quant_method, payload if isinstance(payload, dict) else {}
    return None, {}


def _detect_local(model_path: str) -> tuple[str | None, dict[str, Any]]:
    """Inspect local model files to detect the quantization backend."""
    if not is_local_model_path(model_path):
        return None, {}

    def resolve_local(filename: str) -> str | None:
        candidate = os.path.join(model_path, filename)
        return candidate if os.path.isfile(candidate) else None

    return _detect_from_configs(resolve_local)


def _detect_remote(model_path: str) -> tuple[str | None, dict[str, Any]]:
    """Inspect remote Hugging Face repos for quantization metadata."""
    if not model_path or "/" not in model_path or is_local_model_path(model_path):
        return None, {}

    download_fn = _get_hf_download_fn()
    if download_fn is None:
        return None, {}

    def resolve_remote(filename: str) -> str | None:
        return download_fn(model_path, filename)

    return _detect_from_configs(resolve_remote)


def _extract_quant_config(payload: Any) -> dict[str, Any]:
    """Extract quantization config from a config payload."""
    if not isinstance(payload, dict):
        return {}
    config = payload.get("quantization_config")
    if isinstance(config, dict):
        return config
    return payload


def _extract_quant_method(payload: Any) -> str | None:
    """Extract the declared quantization method from a config payload."""
    if not isinstance(payload, dict):
        return None

    def _from_dict(data: dict[str, Any]) -> str | None:
        for key in ("quantization_method", "quant_method", "quantization"):
            value = data.get(key)
            if isinstance(value, str):
                normalized = _normalize_quant_name(value)
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
        return _normalize_quant_name(nested.get("quantization_method")) or "compressed-tensors"

    return None


def _normalize_quant_name(name: str | None) -> str | None:
    """Normalize various quantization labels to vLLM's expected names."""
    if not name:
        return None
    normalized = name.strip().lower().replace("_", "-")
    return QUANT_NAME_MAPPING.get(normalized)


# ============================================================================
# Sanitization - Remove unsupported fields from quant configs
# ============================================================================


def sanitize_quant_metadata(model_path: str) -> None:
    """Remove unsupported dtype keys from local or cached remote config files."""
    if not model_path:
        return
    if is_local_model_path(model_path):
        _sanitize_local_configs(model_path)
        return
    if "/" not in model_path:
        return
    _sanitize_remote_configs(model_path)


def strip_unsupported_fields(payload: Any) -> bool:
    """Recursively delete unsupported dtype keys from a JSON-compatible object."""

    def _strip(obj: Any) -> bool:
        removed = False
        if isinstance(obj, dict):
            for key in list(obj.keys()):
                if key in UNSUPPORTED_QUANT_DTYPE_FIELDS:
                    obj.pop(key, None)
                    removed = True
            for value in obj.values():
                removed |= _strip(value)
        elif isinstance(obj, list):
            for item in obj:
                removed |= _strip(item)
        return removed

    return _strip(payload)


# ============================================================================
# Detection - Find and parse quantization metadata
# ============================================================================


def detect_quant_backend(model_path: str) -> tuple[str | None, dict[str, Any]]:
    """Detect quantization backend from local or remote model configs.

    Attempts local detection first, then remote HuggingFace if needed.
    Also sanitizes any unsupported dtype fields found.
    """
    sanitize_quant_metadata(model_path)
    method, payload = _detect_local(model_path)
    if method:
        return method, payload
    return _detect_remote(model_path)


def log_quant_detection(model_path: str, method: str, payload: dict[str, Any]) -> None:
    """Log a concise description of the detected quantization metadata."""
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
    logger.info("[config] Detected %s quantization for %s: %s", method, model_path, detail_str)


# ============================================================================
# Resolution - Resolve model origins and normalize quant names
# ============================================================================


def resolve_model_origin(model_path: str) -> str:
    """Best effort to determine the underlying HF repo for local AWQ exports."""
    if not model_path:
        return ""
    if is_local_model_path(model_path):
        meta_path = os.path.join(model_path, AWQ_METADATA_FILENAME)
        payload = read_json_file(meta_path)
        if isinstance(payload, dict):
            source = payload.get("source_model")
            if isinstance(source, str) and source.strip():
                return source.strip()
    return model_path


__all__ = [
    # Sanitization
    "sanitize_quant_metadata",
    "strip_unsupported_fields",
    # Detection
    "detect_quant_backend",
    "log_quant_detection",
    # Resolution
    "resolve_model_origin",
    # Re-exports
    "UNSUPPORTED_QUANT_DTYPE_FIELDS",
]
