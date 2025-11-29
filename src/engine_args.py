"""Engine args builder and related utilities for vLLM engines."""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
from typing import Any

from vllm.engine.arg_utils import AsyncEngineArgs

from .config.env import (
    KV_DTYPE,
    QUANTIZATION,
    CHAT_QUANTIZATION,
    TOOL_QUANTIZATION,
)
from .config.awq import (
    get_model_profile,
    get_tokenizer_kwargs,
    model_needs_memory_optimization,
    model_requires_bfloat16,
    model_requires_fla_runtime,
    normalize_model_id,
)
from .config.quantization import is_lowbit_quantization
from .config.models import _is_local_model_path


_QUANT_CONFIG_CANDIDATES = (
    "config.json",
    "quantization_config.json",
    "quant_config.json",
    "awq_config.json",
)
_AWQ_METADATA_FILE = "awq_metadata.json"
_TOKENIZER_WARNING_EMITTED = False
_TOKENIZER_PATCH_WARNING_EMITTED = False
_FIX_MISTRAL_REGEX_PATCH_INSTALLED = False
_FIX_MISTRAL_REGEX_MARKERS: set[str] = set()
_CUDA_MEM_WARNING_EMITTED = False
_KV_DTYPE_WARNING_EMITTED = False


def _resolve_tokenizer_kwarg_key() -> str | None:
    """Return the AsyncEngineArgs kwarg that accepts tokenizer kwargs."""
    try:
        params = inspect.signature(AsyncEngineArgs.__init__).parameters
    except (ValueError, TypeError):
        return None
    for candidate in ("tokenizer_kwargs", "tokenizer_init_kwargs"):
        if candidate in params:
            return candidate
    return None


_TOKENIZER_KWARG_KEY = _resolve_tokenizer_kwarg_key()


def _inject_tokenizer_kwargs(
    target: dict[str, Any],
    tok_kwargs: dict[str, Any],
    model_identifier: str | None,
) -> None:
    """Attach tokenizer kwargs if the installed vLLM supports them."""
    global _TOKENIZER_WARNING_EMITTED

    if not tok_kwargs:
        return
    if _TOKENIZER_KWARG_KEY:
        target[_TOKENIZER_KWARG_KEY] = tok_kwargs
        return
    if _maybe_patch_tokenizer(model_identifier, tok_kwargs):
        return

    if not _TOKENIZER_WARNING_EMITTED:
        keys = ", ".join(sorted(tok_kwargs.keys()))
        print(
            "[config] Warning: vLLM does not expose tokenizer kwargs; "
            f"skipping tokenizer overrides ({keys or 'unknown keys'})."
        )
        _TOKENIZER_WARNING_EMITTED = True


def _maybe_patch_tokenizer(model_identifier: str | None, tok_kwargs: dict[str, Any]) -> bool:
    """Best-effort tokenizer monkeypatch for engines lacking tokenizer kwargs."""
    if not tok_kwargs:
        return False

    needs_mistral_fix = tok_kwargs.get("fix_mistral_regex")
    if not needs_mistral_fix:
        return False

    markers: set[str] = set()
    profile = get_model_profile(model_identifier) if model_identifier else None
    if profile:
        for marker in profile.markers:
            normalized = normalize_model_id(marker)
            if normalized:
                markers.add(normalized)

    normalized_identifier = normalize_model_id(model_identifier)
    if normalized_identifier:
        markers.add(normalized_identifier)

    if not markers:
        return False

    return _install_fix_mistral_regex_patch(markers)


def _install_fix_mistral_regex_patch(markers: set[str]) -> bool:
    """Monkeypatch AutoTokenizer to force fix_mistral_regex for specific models."""
    global _FIX_MISTRAL_REGEX_PATCH_INSTALLED, _FIX_MISTRAL_REGEX_MARKERS, _TOKENIZER_PATCH_WARNING_EMITTED

    try:
        from transformers import AutoTokenizer  # type: ignore
    except Exception as exc:  # noqa: BLE001
        if not _TOKENIZER_PATCH_WARNING_EMITTED:
            print(
                "[config] Warning: transformers not available to patch tokenizer "
                f"kwargs fallback ({exc})."
            )
            _TOKENIZER_PATCH_WARNING_EMITTED = True
        return False

    markers = {m for m in markers if m}
    if not markers:
        return False

    _FIX_MISTRAL_REGEX_MARKERS.update(markers)

    if _FIX_MISTRAL_REGEX_PATCH_INSTALLED:
        return True

    original = AutoTokenizer.from_pretrained.__func__

    def _patched_from_pretrained(cls, pretrained_model_name_or_path, *args, **kwargs):
        normalized = _normalize_tokenizer_identifier(pretrained_model_name_or_path)
        if normalized and any(marker in normalized for marker in _FIX_MISTRAL_REGEX_MARKERS):
            kwargs.setdefault("fix_mistral_regex", True)
        return original(cls, pretrained_model_name_or_path, *args, **kwargs)

    AutoTokenizer._yap_original_from_pretrained = original  # type: ignore[attr-defined]
    AutoTokenizer.from_pretrained = classmethod(_patched_from_pretrained)
    _FIX_MISTRAL_REGEX_PATCH_INSTALLED = True
    print(
        "[config] Applied AutoTokenizer monkeypatch for fix_mistral_regex "
        f"(markers: {', '.join(sorted(_FIX_MISTRAL_REGEX_MARKERS))})"
    )
    return True


def _normalize_tokenizer_identifier(candidate: Any) -> str:
    """Best-effort normalization for AutoTokenizer inputs."""
    if candidate is None:
        return ""
    if isinstance(candidate, (str, os.PathLike)):
        return normalize_model_id(os.fspath(candidate))

    name_or_path = getattr(candidate, "name_or_path", None)
    if isinstance(name_or_path, str):
        return normalize_model_id(name_or_path)

    return normalize_model_id(str(candidate))


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
        with open(path, encoding="utf-8") as fh:
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


def _detect_local_quantization_backend(model_path: str) -> tuple[str | None, dict[str, Any]]:
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


def _detect_remote_quantization_backend(model_path: str) -> tuple[str | None, dict[str, Any]]:
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


def _detect_quantization_backend(model_path: str) -> tuple[str | None, dict[str, Any]]:
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


def _ensure_fla_runtime_available(model_identifier: str) -> None:
    """Raise a helpful error if fla-core is missing when required."""
    has_fla = importlib.util.find_spec("fla") is not None
    if has_fla:
        return
    raise RuntimeError(
        f"The model '{model_identifier}' requires the flash-linear-attention runtime.\n"
        "Install fla-core>=0.4.0 (included in requirements.txt) before launching the server."
    )


def _read_cuda_memory_snapshot() -> tuple[int, int] | None:
    """Return (free_bytes, total_bytes) for the current CUDA device."""
    global _CUDA_MEM_WARNING_EMITTED
    try:
        import torch  # local import to avoid hard dependency at module import time
    except Exception as exc:  # noqa: BLE001
        if not _CUDA_MEM_WARNING_EMITTED:
            print(f"[config] Warning: torch unavailable for CUDA mem introspection ({exc})")
            _CUDA_MEM_WARNING_EMITTED = True
        return None

    if not torch.cuda.is_available() or torch.cuda.device_count() == 0:
        return None

    try:
        device_index = torch.cuda.current_device() if torch.cuda.is_initialized() else 0
        with torch.cuda.device(device_index):
            free_bytes, total_bytes = torch.cuda.mem_get_info()
        return int(free_bytes), int(total_bytes)
    except Exception as exc:  # noqa: BLE001
        if not _CUDA_MEM_WARNING_EMITTED:
            print(f"[config] Warning: unable to read torch.cuda.mem_get_info ({exc})")
            _CUDA_MEM_WARNING_EMITTED = True
        return None


def _scale_batching_limits(
    *,
    max_tokens: int,
    max_seqs: int | None,
    gpu_frac: float,
    engine_role: str,
) -> tuple[int, int | None]:
    """Shrink batching knobs when available memory is below the target budget."""
    snapshot = _read_cuda_memory_snapshot()
    if not snapshot or gpu_frac <= 0:
        return max_tokens, max_seqs

    free_bytes, total_bytes = snapshot
    target_bytes = max(int(total_bytes * min(gpu_frac, 0.99)), 1)
    if free_bytes >= target_bytes:
        return max_tokens, max_seqs

    ratio = max(free_bytes / target_bytes, 0.1)
    scaled_tokens = max(64, int(max_tokens * ratio))
    scaled_seqs = None
    if max_seqs is not None:
        scaled_seqs = max(4, int(max_seqs * ratio))

    print(
        "[config] Scaling %s batching limits to %.2fx (free %.1f GiB vs budget %.1f GiB)"
        % (
            engine_role,
            ratio,
            free_bytes / (1024**3),
            target_bytes / (1024**3),
        )
    )
    return scaled_tokens, scaled_seqs


def _configure_kv_cache(kwargs: dict[str, Any], kv_dtype: str, use_v1: bool) -> None:
    """Attach the appropriate KV cache controls based on engine mode."""
    global _KV_DTYPE_WARNING_EMITTED
    normalized = kv_dtype.strip().lower()
    if not normalized or normalized == "auto":
        return

    if use_v1:
        if normalized.startswith("fp8"):
            kwargs["fp8_kv_cache"] = True
            os.environ.setdefault("VLLM_FP8_KV_CACHE_ENABLE", "1")
        else:
            if not _KV_DTYPE_WARNING_EMITTED:
                print(
                    "[config] Warning: kv_cache_dtype=%s is ignored by the V1 engine. "
                    "Set VLLM_USE_V1=0 to use legacy int8/fp8 switches."
                    % normalized
                )
                _KV_DTYPE_WARNING_EMITTED = True
        return

    kwargs["kv_cache_dtype"] = normalized
    if normalized.startswith("fp8"):
        kwargs["calculate_kv_scales"] = True


def make_engine_args(model: str, gpu_frac: float, max_len: int, is_chat: bool) -> AsyncEngineArgs:
    # Prefill chunk sizing (smaller chunk => better TTFB under burst; tune as needed)
    max_batched = int(os.getenv(
        "MAX_NUM_BATCHED_TOKENS_CHAT" if is_chat else "MAX_NUM_BATCHED_TOKENS_TOOL",
        "512" if is_chat else "256",
    ))

    # Normalize/validate KV cache dtype
    kv_dtype_value = (KV_DTYPE or "").strip()  # empty => let vLLM decide

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
    needs_bfloat16 = model_requires_bfloat16(model_origin)
    needs_memory_opt = model_needs_memory_optimization(model_origin)
    needs_mla = model_requires_fla_runtime(model_origin)  # MLA = Multi-Head Latent Attention
    if needs_mla:
        _ensure_fla_runtime_available(model_origin)
        # MLA models don't work with XFORMERS or FLASHINFER backends
        # Unset the backend to let vLLM auto-select the appropriate backend for MLA
        # vLLM will automatically use FLASH_ATTN when MLA is detected
        if os.getenv("VLLM_ATTENTION_BACKEND"):
            os.environ.pop("VLLM_ATTENTION_BACKEND", None)

    dtype_value = "auto"
    # Models that require bfloat16 (e.g., Gemma3) must use it even when quantized
    # For other quantized models, prefer fp16 (Marlin performs better with fp16 on SM < 9.0)
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

    # Apply model-specific tokenizer kwargs if supported by vLLM
    tok_kwargs = get_tokenizer_kwargs(model_origin)
    _inject_tokenizer_kwargs(kwargs, tok_kwargs, model_origin)

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

    use_v1 = (os.getenv("VLLM_USE_V1", "1") == "1")
    _configure_kv_cache(kwargs, kv_dtype_value, use_v1)

    scaled_tokens, scaled_max_seqs = _scale_batching_limits(
        max_tokens=kwargs["max_num_batched_tokens"],
        max_seqs=kwargs.get("max_num_seqs"),
        gpu_frac=kwargs["gpu_memory_utilization"],
        engine_role="chat" if is_chat else "tool",
    )
    kwargs["max_num_batched_tokens"] = scaled_tokens
    if scaled_max_seqs is not None:
        kwargs["max_num_seqs"] = scaled_max_seqs

    engine_args = AsyncEngineArgs(**kwargs)

    # Add flag for local AWQ handling in engine creation
    if raw_quant == "awq" and _is_local_model_path(model):
        engine_args._is_local_awq = True

    return engine_args


__all__ = ["make_engine_args"]

