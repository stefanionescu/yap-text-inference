"""Engine args builder and related utilities for vLLM engines."""

import importlib.util
import json
import os
from typing import Any, Tuple

from vllm.engine.arg_utils import AsyncEngineArgs

from .env import (
    KV_DTYPE,
    QUANTIZATION,
    CHAT_QUANTIZATION,
    TOOL_QUANTIZATION,
)
from .quantization import is_lowbit_quantization
from .models import _is_local_model_path


_QUANT_CONFIG_CANDIDATES = (
    "config.json",
    "quantization_config.json",
    "quant_config.json",
    "awq_config.json",
)
_AWQ_METADATA_FILE = "awq_metadata.json"


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
        # Fallback: llmcompressor often stores quant info only in nested config
        return _normalize_quantization_name(nested.get("quantization_method")) or "compressed-tensors"

    return None


def _read_json_file(path: str) -> dict[str, Any] | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _extract_quant_config(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    config = payload.get("quantization_config")
    if isinstance(config, dict):
        return config
    return payload if isinstance(payload, dict) else {}


def _log_detected_quantization(model_path: str, method: str, payload: dict[str, Any]) -> None:
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


def _detect_local_quantization_backend(model_path: str) -> Tuple[str | None, dict[str, Any]]:
    """Inspect local model files to detect the quantization backend."""
    if not _is_local_model_path(model_path):
        return None, {}

    for filename in _QUANT_CONFIG_CANDIDATES:
        candidate = os.path.join(model_path, filename)
        if not os.path.isfile(candidate):
            continue
        payload = _read_json_file(candidate)
        if payload is None:
            continue
        quant_method = _extract_quantization_method(payload)
        if quant_method:
            return quant_method, payload if isinstance(payload, dict) else {}
    return None, {}


def _detect_remote_quantization_backend(model_path: str) -> Tuple[str | None, dict[str, Any]]:
    """Inspect remote Hugging Face repos for quantization metadata."""
    if not model_path or "/" not in model_path or _is_local_model_path(model_path):
        return None, {}
    try:
        from huggingface_hub import hf_hub_download  # type: ignore
    except Exception as exc:  # noqa: BLE001
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
        payload = _read_json_file(downloaded)
        if payload is None:
            continue
        quant_method = _extract_quantization_method(payload)
        if quant_method:
            return quant_method, payload
    return None, {}


def _detect_quantization_backend(model_path: str) -> Tuple[str | None, dict[str, Any]]:
    """Attempt both local and remote detection for llmcompressor exports."""
    method, payload = _detect_local_quantization_backend(model_path)
    if method:
        return method, payload
    return _detect_remote_quantization_backend(model_path)


def _resolve_model_origin(model_path: str) -> str:
    """Best effort to determine the underlying HF repo for local AWQ exports."""
    if not model_path:
        return ""
    if _is_local_model_path(model_path):
        meta_path = os.path.join(model_path, _AWQ_METADATA_FILE)
        payload = _read_json_file(meta_path)
        if isinstance(payload, dict):
            source = payload.get("source_model")
            if isinstance(source, str) and source.strip():
                return source.strip()
    return model_path


def _requires_bfloat16(model_identifier: str) -> bool:
    """Return True when the model architecture mandates bfloat16 activations."""
    ident = (model_identifier or "").lower()
    if not ident:
        return False
    if "gemma-3" in ident or "gemma3" in ident:
        return True
    if "kimi-linear" in ident or "kimi_linear" in ident:
        return True
    return False


def _requires_fla_runtime(model_identifier: str) -> bool:
    """Detect models that need the flash-linear-attention runtime."""
    ident = (model_identifier or "").lower()
    if not ident:
        return False
    return "kimi-linear" in ident or "kimi_linear" in ident


def _needs_memory_optimization(model_identifier: str) -> bool:
    """Return True for models that need reduced max_num_seqs to avoid OOM."""
    ident = (model_identifier or "").lower()
    if not ident:
        return False
    # Gemma models often OOM during warmup with default max_num_seqs
    if "gemma" in ident:
        return True
    return False


def _ensure_fla_runtime_available(model_identifier: str) -> None:
    """Raise a helpful error if fla-core is missing when required."""
    has_fla = importlib.util.find_spec("fla") is not None
    if has_fla:
        return
    raise RuntimeError(
        f"The model '{model_identifier}' requires the flash-linear-attention runtime.\n"
        "Install fla-core>=0.4.0 (included in requirements.txt) before launching the server."
    )


def make_engine_args(model: str, gpu_frac: float, max_len: int, is_chat: bool) -> AsyncEngineArgs:

    # Prefill chunk sizing (smaller chunk => better TTFB under burst; tune as needed)
    max_batched = int(os.getenv(
        "MAX_NUM_BATCHED_TOKENS_CHAT" if is_chat else "MAX_NUM_BATCHED_TOKENS_TOOL",
        "512" if is_chat else "256",
    ))

    # Normalize/validate KV cache dtype
    kv_dtype = (KV_DTYPE or "").strip().lower()  # empty => let vLLM decide

    # Select per-engine quantization:
    # - If CHAT_QUANTIZATION/TOOL_QUANTIZATION is set, prefer that.
    # - Else default: chat uses QUANTIZATION; tool inherits QUANTIZATION for low-bit modes.
    if is_chat:
        selected_quant = (CHAT_QUANTIZATION or QUANTIZATION)
    else:
        if TOOL_QUANTIZATION:
            selected_quant = TOOL_QUANTIZATION
        elif is_lowbit_quantization(QUANTIZATION):
            selected_quant = QUANTIZATION
        else:
            selected_quant = None

    raw_quant = selected_quant
    inference_quant = raw_quant
    if raw_quant == "awq":
        inference_quant = "awq_marlin"
        detected_quant, quant_payload = _detect_quantization_backend(model)
        if detected_quant:
            inference_quant = detected_quant
            _log_detected_quantization(model, detected_quant, quant_payload)

    model_origin = _resolve_model_origin(model)
    needs_bfloat16 = _requires_bfloat16(model_origin)
    needs_memory_opt = _needs_memory_optimization(model_origin)
    needs_mla = _requires_fla_runtime(model_origin)  # MLA = Multi-Head Latent Attention
    if needs_mla:
        _ensure_fla_runtime_available(model_origin)
        # MLA models don't work with XFORMERS or FLASHINFER backends
        # Unset the backend to let vLLM auto-select the appropriate backend for MLA
        # vLLM will automatically use FLASH_ATTN when MLA is detected
        if os.getenv("VLLM_ATTENTION_BACKEND"):
            os.environ.pop("VLLM_ATTENTION_BACKEND", None)

    dtype_value = "auto"
    if needs_bfloat16:
        dtype_value = "bfloat16"
    elif inference_quant in {"awq", "awq_marlin", "compressed-tensors"}:
        dtype_value = "float16"

    # Build kwargs for V1 engine.
    kwargs = dict(
        model=model,
        trust_remote_code=True,
        tensor_parallel_size=1,
        max_model_len=max_len,
        gpu_memory_utilization=gpu_frac,
        # Allow CUDA graphs for better performance
        enforce_eager=False,
        enable_chunked_prefill=True,
        max_num_batched_tokens=max_batched,
        # Always enable prefix caching for performance
        enable_prefix_caching=True,
        # Weight quantization (None => float weights)
        quantization=inference_quant,
        dtype=dtype_value,
        # Enable per-request priorities used by generate(..., priority=...)
        scheduling_policy="priority",
    )

    # Memory optimization for models prone to OOM (e.g., Gemma)
    # Lower max_num_seqs to reduce memory pressure during warmup
    if needs_memory_opt:
        # Allow override via env var, otherwise use conservative default
        # Check engine-specific var first, then global, then default to 64
        env_key = "MAX_NUM_SEQS_CHAT" if is_chat else "MAX_NUM_SEQS_TOOL"
        max_num_seqs = int(os.getenv(env_key) or os.getenv("MAX_NUM_SEQS", "64"))
        kwargs["max_num_seqs"] = max_num_seqs
        # Slightly reduce GPU memory utilization for Gemma if not already lowered
        if gpu_frac > 0.85:
            kwargs["gpu_memory_utilization"] = min(gpu_frac, 0.85)

    # Special handling for local AWQ models to avoid Hugging Face repo ID validation
    if raw_quant == "awq" and _is_local_model_path(model):
        # For local AWQ models, ensure the path is absolute so vLLM treats it as local
        kwargs["model"] = os.path.abspath(model)

    # Only pass kv_cache_dtype if explicitly set AND V1 is off
    # (V1 rejects --kv-cache-dtype and will throw NotImplementedError)
    use_v1 = (os.getenv("VLLM_USE_V1", "1") == "1")
    if (not use_v1) and kv_dtype:
        kwargs["kv_cache_dtype"] = kv_dtype
        # Add KV scale calculation for FP8 KV cache
        if kv_dtype.startswith("fp8"):
            # Enable dynamic k/v scale calculation for FP8 KV cache
            kwargs["calculate_kv_scales"] = True

    engine_args = AsyncEngineArgs(**kwargs)

    # Add flag for local AWQ handling in engine creation
    if raw_quant == "awq" and _is_local_model_path(model):
        engine_args._is_local_awq = True

    return engine_args


__all__ = ["make_engine_args"]


