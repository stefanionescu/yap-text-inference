"""Metadata collection for TRT-LLM quantized models."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import trt as trt_config
from src.helpers.templates import compute_license_info

from ..utils.detection import (
    detect_cuda_version,
    detect_gpu_name,
    detect_tensorrt_llm_version,
    get_compute_capability_info,
)


class EngineLabelError(Exception):
    """Raised when engine label cannot be determined."""
    

def _env_int(name: str, default: int | None) -> int | None:
    """Get int from env var, handling empty strings."""
    val = os.getenv(name, "")
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    """Get string from env var, handling empty strings."""
    val = os.getenv(name, "")
    return val if val else default


def detect_base_model(checkpoint_path: Path) -> str:
    """Detect base model from checkpoint config.
    
    Args:
        checkpoint_path: Path to TRT-LLM checkpoint directory.
        
    Returns:
        Base model ID or "unknown".
    """
    config_path = checkpoint_path / "config.json"
    if config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            # TRT-LLM config may have pretrained_config with model info
            pretrained = config.get("pretrained_config", {})
            if "model_name" in pretrained:
                return pretrained["model_name"]
        except Exception:
            pass
    return "unknown"


@dataclass
class _EnvironmentInfo:
    """Container for environment-detected build information."""
    sm_arch: str
    trt_version: str
    cuda_version: str
    gpu_name: str = field(default_factory=detect_gpu_name)
    
    @classmethod
    def from_env(cls) -> "_EnvironmentInfo":
        """Load environment info, raising EngineLabelError if required vars missing."""
        sm_arch = os.getenv("GPU_SM_ARCH")
        if not sm_arch:
            raise EngineLabelError(
                "GPU_SM_ARCH not set. This should be exported by gpu_init_detection() "
                "in scripts/lib/common/gpu_detect.sh."
            )
        
        trt_version = os.getenv("TRT_VERSION") or detect_tensorrt_llm_version()
        if not trt_version or trt_version == "unknown":
            raise EngineLabelError(
                "TRT_VERSION not set and tensorrt_llm not importable. "
                "This should be set in scripts/lib/env/trt.sh."
            )
        
        cuda_version = os.getenv("CUDA_VERSION") or detect_cuda_version()
        if not cuda_version or cuda_version == "unknown":
            raise EngineLabelError(
                "CUDA_VERSION not set and nvcc not found. "
                "Ensure CUDA is installed or CUDA_VERSION is exported."
            )
        
        return cls(
            sm_arch=sm_arch,
            trt_version=trt_version,
            cuda_version=cuda_version,
        )
    
    def make_label(self) -> str:
        """Generate the engine label string."""
        return f"{self.sm_arch}_trt-llm-{self.trt_version}_cuda{self.cuda_version}"


def get_engine_label(engine_path: Path) -> str:
    """Generate engine label from build metadata or environment variables.
    
    Args:
        engine_path: Path to TRT-LLM engine directory.
        
    Returns:
        Engine label string (e.g., "sm90_trt-llm-0.17.0_cuda12.8").
        
    Raises:
        EngineLabelError: If required values cannot be determined.
    """
    # Try build_metadata.json first - it has the exact values used at build time
    meta_path = engine_path / "build_metadata.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            sm = meta.get("sm_arch")
            trt_ver = meta.get("tensorrt_llm_version")
            cuda_ver = meta.get("cuda_toolkit") or meta.get("cuda_version")
            
            if sm and trt_ver and cuda_ver:
                return f"{sm}_trt-llm-{trt_ver}_cuda{cuda_ver}"
        except Exception:
            pass
    
    # Fall back to environment
    env_info = _EnvironmentInfo.from_env()
    return env_info.make_label()


def _infer_kv_cache_dtype(quant_method: str) -> str:
    """Infer KV cache dtype from quantization method."""
    env_override = os.getenv("TRT_KV_CACHE_DTYPE")
    if env_override:
        return env_override
    if "fp8" in (quant_method or "").lower():
        return "fp8"
    return "int8"


def _infer_weight_bits(quant_method: str) -> str:
    """Infer weight bit precision from quantization method."""
    if "int4" in quant_method or "awq" in quant_method:
        return "4"
    if "int8" in quant_method:
        return "8"
    if "fp8" in quant_method:
        return "8 (FP8)"
    return "unknown"


def _collect_base_metadata(
    base_model: str,
    repo_id: str,
    quant_method: str,
) -> dict[str, Any]:
    """Collect basic model identification metadata."""
    model_name = base_model if base_model else (repo_id.split("/")[-1] if "/" in repo_id else repo_id)
    source_link = f"https://huggingface.co/{base_model}" if "/" in base_model else base_model
    
    return {
        "base_model": base_model,
        "repo_id": repo_id,
        "model_name": model_name,
        "source_model_link": source_link,
        "quant_method": quant_method,
        "quant_method_upper": quant_method.upper().replace("_", "-"),
        "w_bit": _infer_weight_bits(quant_method),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


def _collect_checkpoint_limits(checkpoint_path: Path) -> dict[str, Any]:
    """Read build limits from checkpoint config.json."""
    limits: dict[str, Any] = {}
    config_path = checkpoint_path / "config.json"
    
    if config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            build_cfg = config.get("build_config", {})
            limits["max_batch_size"] = build_cfg.get("max_batch_size", "N/A")
            limits["max_input_len"] = build_cfg.get("max_input_len", "N/A")
            limits["max_output_len"] = build_cfg.get("max_seq_len", "N/A")
        except Exception:
            pass
    
    return limits


def _collect_env_metadata(
    quant_method: str,
    checkpoint_limits: dict[str, Any],
) -> dict[str, Any]:
    """Collect metadata from environment variables and runtime detection."""
    env_info = _EnvironmentInfo.from_env()
    
    return {
        "sm_arch": env_info.sm_arch,
        "gpu_name": env_info.gpu_name,
        "cuda_toolkit": env_info.cuda_version,
        "tensorrt_llm_version": env_info.trt_version,
        "kv_cache_dtype": _infer_kv_cache_dtype(quant_method),
        "awq_block_size": _env_int("TRT_AWQ_BLOCK_SIZE", trt_config.TRT_AWQ_BLOCK_SIZE),
        "calib_size": _env_int("TRT_CALIB_SIZE", trt_config.TRT_CALIB_SIZE),
        "calib_seqlen": _env_int("TRT_CALIB_SEQLEN", trt_config.TRT_CALIB_SEQLEN),
        "calib_batch_size": _env_int("TRT_CALIB_BATCH_SIZE", trt_config.TRT_CALIB_BATCH_SIZE),
        "max_batch_size": _env_str(
            "TRT_MAX_BATCH_SIZE",
            str(checkpoint_limits.get("max_batch_size", trt_config.TRT_MAX_BATCH_SIZE or "N/A")),
        ),
        "max_input_len": _env_str(
            "TRT_MAX_INPUT_LEN",
            str(checkpoint_limits.get("max_input_len", trt_config.TRT_MAX_INPUT_LEN)),
        ),
        "max_output_len": _env_str(
            "TRT_MAX_OUTPUT_LEN",
            str(checkpoint_limits.get("max_output_len", trt_config.TRT_MAX_OUTPUT_LEN)),
        ),
    }


def _apply_build_metadata_overrides(
    metadata: dict[str, Any],
    engine_path: Path,
) -> None:
    """Override metadata with values from build_metadata.json if available."""
    if not engine_path.is_dir():
        return
    
    meta_path = engine_path / "build_metadata.json"
    if not meta_path.is_file():
        return
    
    try:
        build_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return
    
    # Fields that can be overridden from build metadata
    override_keys = [
        ("sm_arch", "sm_arch"),
        ("gpu_name", "gpu_name"),
        ("cuda_toolkit", "cuda_toolkit"),
        ("cuda_toolkit", "cuda_version"),  # Alternative key
        ("tensorrt_llm_version", "tensorrt_llm_version"),
        ("kv_cache_dtype", "kv_cache_dtype"),
        ("awq_block_size", "awq_block_size"),
        ("calib_size", "calib_size"),
        ("calib_seqlen", "calib_seqlen"),
        ("calib_batch_size", "calib_batch_size"),
        ("max_batch_size", "max_batch_size"),
        ("max_input_len", "max_input_len"),
        ("max_output_len", "max_output_len"),
        ("max_output_len", "max_seq_len"),  # Alternative key
    ]
    
    for target_key, source_key in override_keys:
        if source_key in build_meta and build_meta[source_key] is not None:
            metadata[target_key] = build_meta[source_key]
    
    # Update compute capability info if sm_arch changed
    if "sm_arch" in build_meta:
        metadata.update(get_compute_capability_info(metadata["sm_arch"]))


def collect_metadata(
    checkpoint_path: Path,
    engine_path: Path,
    base_model: str,
    repo_id: str,
    quant_method: str,
) -> dict[str, Any]:
    """Collect metadata for README rendering.
    
    Args:
        checkpoint_path: Path to TRT-LLM checkpoint directory.
        engine_path: Path to TRT-LLM engine directory.
        base_model: Base model ID.
        repo_id: HuggingFace repo ID.
        quant_method: Quantization method (e.g., "int4_awq").
        
    Returns:
        Dictionary of metadata for template rendering.
    """
    # Collect base identification metadata
    metadata = _collect_base_metadata(base_model, repo_id, quant_method)
    
    # Collect limits from checkpoint config
    checkpoint_limits = _collect_checkpoint_limits(checkpoint_path)
    metadata.update(checkpoint_limits)
    
    # Collect environment/runtime metadata
    env_metadata = _collect_env_metadata(quant_method, checkpoint_limits)
    metadata.update(env_metadata)
    
    # Add compute capability info
    metadata.update(get_compute_capability_info(metadata["sm_arch"]))
    
    # Generate engine label
    if engine_path.is_dir():
        metadata["engine_label"] = get_engine_label(engine_path)
        # Apply any overrides from build_metadata.json
        _apply_build_metadata_overrides(metadata, engine_path)
    else:
        # Engine path doesn't exist yet - generate label from environment
        env_info = _EnvironmentInfo.from_env()
        metadata["engine_label"] = env_info.make_label()
    
    # Fetch license from the base model
    is_hf_model = "/" in base_model
    license_info = compute_license_info(base_model, is_tool=False, is_hf_model=is_hf_model)
    metadata.update(license_info)

    metadata.setdefault(
        "quant_portability_note",
        "INT4-AWQ checkpoints are portable across sm89/sm90+ GPUs; rebuild engines for the target GPU (e.g., H100/H200/B200/Blackwell, L40S, 4090/RTX) or reuse one of the prebuild engines in case they match your GPU.",
    )
    
    return metadata
