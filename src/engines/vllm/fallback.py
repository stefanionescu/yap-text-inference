"""Engine creation fallback helpers for handling legacy configs.

This module provides helpers for:
1. Local AWQ model loading (forcing offline mode)
2. Stripping unsupported quantization dtype fields from engine args
"""

from __future__ import annotations

import contextlib
import logging
import os
from copy import deepcopy
from typing import Any

from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine

from src.config import QUANT_CONFIG_FILENAMES, UNSUPPORTED_QUANT_DTYPE_FIELDS
from src.helpers.io import read_json_file
from src.helpers.models import is_local_model_path
from src.quantization.vllm.core.detection import strip_unsupported_fields

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _local_model_offline_context():
    """Temporarily force offline flags for local model loading.
    
    This prevents HuggingFace Hub from trying to fetch remote files
    when loading a local AWQ-quantized model.
    """
    original_offline = os.environ.get("HF_HUB_OFFLINE")
    original_transformers_offline = os.environ.get("TRANSFORMERS_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        yield
    finally:
        if original_offline is not None:
            os.environ["HF_HUB_OFFLINE"] = original_offline
        else:
            os.environ.pop("HF_HUB_OFFLINE", None)
        if original_transformers_offline is not None:
            os.environ["TRANSFORMERS_OFFLINE"] = original_transformers_offline
        else:
            os.environ.pop("TRANSFORMERS_OFFLINE", None)


def _get_engine_args_field_names(engine_args: AsyncEngineArgs) -> list[str]:
    """Get the field names from engine args (annotations or instance dict)."""
    annotations = getattr(engine_args.__class__, "__annotations__", {}) or {}
    names = list(annotations) or list(getattr(engine_args, "__dict__", {}).keys())
    if "quantization_config" not in names and hasattr(engine_args, "quantization_config"):
        names.append("quantization_config")
    return names


def _strip_fields_from_dict(data: Any) -> bool:
    """Recursively strip unsupported quant dtype fields (dicts or lists).
    
    Delegates to the shared quantization sanitization helper so that
    list-valued configs (e.g., layer-wise settings) are handled too.
    """
    try:
        return strip_unsupported_fields(data)
    except Exception:
        return False


def _sanitize_config_file_in_place(path: str) -> bool:
    """Sanitize a single config file by removing unsupported fields.
    
    Returns True if file was modified.
    """
    import stat
    
    payload = read_json_file(path)
    if not payload or not isinstance(payload, dict):
        return False
    
    if not _strip_fields_from_dict(payload):
        return False
    
    # HF cache blobs are often read-only; try to make writable before writing
    original_mode = None
    try:
        file_stat = os.stat(path)
        if not (file_stat.st_mode & stat.S_IWUSR):
            original_mode = file_stat.st_mode
            os.chmod(path, file_stat.st_mode | stat.S_IWUSR)
    except OSError:
        pass
    
    from src.helpers.io import write_json_file
    success = write_json_file(path, payload)
    
    # Restore original permissions if we changed them
    if original_mode is not None:
        try:
            os.chmod(path, original_mode)
        except OSError:
            pass
    
    return success


def _sanitize_model_configs(model_path: str) -> bool:
    """Sanitize all config files for a model (local or HF cached).
    
    Returns True if any files were sanitized.
    """
    if not model_path:
        return False
    
    sanitized = False
    
    if is_local_model_path(model_path):
        # Local model - sanitize files directly
        for filename in QUANT_CONFIG_FILENAMES:
            candidate = os.path.join(model_path, filename)
            if os.path.isfile(candidate):
                if _sanitize_config_file_in_place(candidate):
                    logger.info("Sanitized %s (removed scale_dtype/zp_dtype)", candidate)
                    sanitized = True
    else:
        # HF model - find and sanitize cached files
        try:
            from huggingface_hub import hf_hub_download
            token = os.getenv("HUGGINGFACE_HUB_TOKEN") or os.getenv("HF_TOKEN")
            cache_dir = os.getenv("HF_HOME")
            
            for filename in QUANT_CONFIG_FILENAMES:
                try:
                    cached_path = hf_hub_download(
                        repo_id=model_path,
                        filename=filename,
                        token=token,
                        cache_dir=cache_dir,
                        local_files_only=True,
                    )
                    if _sanitize_config_file_in_place(cached_path):
                        logger.info("Sanitized %s (removed scale_dtype/zp_dtype)", cached_path)
                        sanitized = True
                except Exception:
                    continue
        except ImportError:
            pass
    
    return sanitized


def _clean_quantization_config(value: Any) -> tuple[Any, bool]:
    """Return a sanitized copy of quantization_config and whether it changed."""
    if value is None:
        return value, False
    
    # Convert Pydantic/dataclass objects to plain data for mutation
    for attr in ("model_dump", "dict"):
        if hasattr(value, attr):
            try:
                value = getattr(value, attr)()
                break
            except Exception:
                pass
    else:
        if not isinstance(value, (dict, list)) and hasattr(value, "__dict__"):
            value = dict(getattr(value, "__dict__", {}))
    
    if not isinstance(value, (dict, list)):
        return value, False
    
    cleaned = deepcopy(value)
    removed = _strip_fields_from_dict(cleaned)
    return cleaned, removed


def _strip_unsupported_quant_dtype_fields(engine_args: AsyncEngineArgs) -> AsyncEngineArgs | None:
    """Rebuild engine args without unsupported quant dtype fields.

    vLLM V1 rejects scale_dtype and zp_dtype. Some quantized exports
    still carry these keys, so we strip them and retry engine creation.
    
    Returns None if no fields were removed (nothing to retry).
    """
    # First, try to sanitize the model config files directly
    model_path = getattr(engine_args, "model", None)
    files_sanitized = _sanitize_model_configs(model_path) if model_path else False
    
    # Now rebuild engine args, stripping any unsupported fields
    source_names = _get_engine_args_field_names(engine_args)
    filtered_kwargs: dict[str, Any] = {}
    fields_removed = False

    for name in source_names:
        if name in UNSUPPORTED_QUANT_DTYPE_FIELDS:
            fields_removed = True
            continue
        if not hasattr(engine_args, name):
            continue

        value = getattr(engine_args, name)
        
        # Clean nested quantization_config payloads (dicts, lists, pydantic)
        if name == "quantization_config":
            value, removed = _clean_quantization_config(value)
            fields_removed |= removed

        filtered_kwargs[name] = value

    if not files_sanitized and not fields_removed:
        return None

    new_args = AsyncEngineArgs(**filtered_kwargs)
    if hasattr(engine_args, "_is_local_awq"):
        new_args._is_local_awq = engine_args._is_local_awq
    return new_args


def _is_unsupported_quant_dtype_error(error: Exception) -> bool:
    """Check if error is a ValidationError about unsupported quant dtype fields."""
    if error.__class__.__name__ != "ValidationError":
        return False
    message = str(error)
    return bool(message) and any(field in message for field in UNSUPPORTED_QUANT_DTYPE_FIELDS)


def create_engine_with_fallback(engine_args: AsyncEngineArgs) -> AsyncLLMEngine:
    """Create an engine with fallback for unsupported quant dtype fields.
    
    Handles two cases:
    1. Local AWQ models need offline mode to prevent Hub lookups
    2. Legacy quant configs with scale_dtype/zp_dtype need those fields stripped
    """
    def _build(args: AsyncEngineArgs) -> AsyncLLMEngine:
        is_local_awq = getattr(args, "_is_local_awq", False)
        ctx = _local_model_offline_context() if is_local_awq else contextlib.nullcontext()
        with ctx:
            return AsyncLLMEngine.from_engine_args(args)

    try:
        return _build(engine_args)
    except Exception as exc:  # noqa: BLE001
        if not _is_unsupported_quant_dtype_error(exc):
            raise
        fallback_args = _strip_unsupported_quant_dtype_fields(engine_args)
        if fallback_args is None:
            raise
        logger.warning(
            "vLLM: engine args include unsupported quant dtype knobs; retrying without scale/zp dtype fields"
        )
        return _build(fallback_args)


__all__ = ["create_engine_with_fallback"]

