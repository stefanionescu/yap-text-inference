"""Metadata collection for TRT-LLM quantized models."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.helpers.templates import compute_license_info

from ..utils.detection import (
    detect_cuda_version,
    detect_gpu_name,
    detect_tensorrt_llm_version,
    get_compute_capability_info,
)


def _env_int(name: str, default: int) -> int:
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


def get_engine_label(engine_path: Path) -> str:
    """Generate engine label from build metadata.
    
    Args:
        engine_path: Path to TRT-LLM engine directory.
        
    Returns:
        Engine label string (e.g., "sm90_trt-llm-0.17.0_cuda12.8").
    """
    meta_path = engine_path / "build_metadata.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            sm = meta.get("sm_arch", "sm89")
            trt_ver = meta.get("tensorrt_llm_version", "unknown")
            cuda_ver = meta.get("cuda_toolkit", meta.get("cuda_version", "unknown"))
            return f"{sm}_trt-llm-{trt_ver}_cuda{cuda_ver}"
        except Exception:
            pass
    
    # Fallback: use directory name or generate from env
    sm = os.getenv("GPU_SM_ARCH", "sm89")
    return f"{sm}_default"


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
    metadata = {
        "base_model": base_model,
        "repo_id": repo_id,
        "model_name": base_model if base_model else (repo_id.split("/")[-1] if "/" in repo_id else repo_id),
        "source_model_link": f"https://huggingface.co/{base_model}" if "/" in base_model else base_model,
        "quant_method": quant_method,
        "quant_method_upper": quant_method.upper().replace("_", "-"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    
    # Detect w_bit from quant method
    if "int4" in quant_method or "awq" in quant_method:
        metadata["w_bit"] = "4"
    elif "int8" in quant_method:
        metadata["w_bit"] = "8"
    elif "fp8" in quant_method:
        metadata["w_bit"] = "8 (FP8)"
    else:
        metadata["w_bit"] = "unknown"
    
    # Read checkpoint config for build limits
    config_path = checkpoint_path / "config.json"
    if config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            build_cfg = config.get("build_config", {})
            metadata["max_batch_size"] = build_cfg.get("max_batch_size", "N/A")
            metadata["max_input_len"] = build_cfg.get("max_input_len", "N/A")
            metadata["max_output_len"] = build_cfg.get("max_seq_len", "N/A")
        except Exception:
            pass
    
    # Set defaults from environment/runtime detection
    sm_arch = _env_str("GPU_SM_ARCH", "sm90")
    trt_version = detect_tensorrt_llm_version()
    cuda_version = _env_str("CUDA_VERSION", detect_cuda_version())
    
    metadata.update({
        "sm_arch": sm_arch,
        "gpu_name": detect_gpu_name(),
        "cuda_toolkit": cuda_version,
        "tensorrt_llm_version": trt_version,
        "kv_cache_dtype": "int8",
        "awq_block_size": _env_int("TRT_AWQ_BLOCK_SIZE", 128),
        "calib_size": _env_int("TRT_CALIB_SIZE", 256),
        "calib_seqlen": 2048,
        "calib_batch_size": _env_int("TRT_CALIB_BATCH_SIZE", 16),
        "max_batch_size": _env_str("TRT_MAX_BATCH_SIZE", str(metadata.get("max_batch_size", "N/A"))),
        "max_input_len": _env_str("TRT_MAX_INPUT_LEN", str(metadata.get("max_input_len", "N/A"))),
        "max_output_len": _env_str("TRT_MAX_OUTPUT_LEN", str(metadata.get("max_output_len", "N/A"))),
    })
    metadata.update(get_compute_capability_info(sm_arch))
    
    # Override with build_metadata.json if available
    if engine_path.is_dir():
        metadata["engine_label"] = get_engine_label(engine_path)
        meta_path = engine_path / "build_metadata.json"
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                sm_arch = meta.get("sm_arch", sm_arch)
                metadata.update({
                    "sm_arch": sm_arch,
                    "gpu_name": meta.get("gpu_name", metadata["gpu_name"]),
                    "cuda_toolkit": meta.get("cuda_toolkit", meta.get("cuda_version", metadata["cuda_toolkit"])),
                    "tensorrt_llm_version": meta.get("tensorrt_llm_version", metadata["tensorrt_llm_version"]),
                    "kv_cache_dtype": meta.get("kv_cache_dtype", metadata["kv_cache_dtype"]),
                    "awq_block_size": meta.get("awq_block_size", metadata["awq_block_size"]),
                    "calib_size": meta.get("calib_size", metadata["calib_size"]),
                    "calib_seqlen": meta.get("calib_seqlen", metadata["calib_seqlen"]),
                    "calib_batch_size": meta.get("calib_batch_size", metadata["calib_batch_size"]),
                    "max_batch_size": meta.get("max_batch_size", metadata["max_batch_size"]),
                    "max_input_len": meta.get("max_input_len", metadata["max_input_len"]),
                    "max_output_len": meta.get("max_seq_len", metadata["max_output_len"]),
                })
                metadata.update(get_compute_capability_info(sm_arch))
            except Exception:
                pass
    else:
        metadata["engine_label"] = f"{sm_arch}_default"
    
    # Fetch license from the base model
    is_hf_model = "/" in base_model
    license_info = compute_license_info(base_model, is_tool=False, is_hf_model=is_hf_model)
    metadata.update(license_info)

    metadata.setdefault(
        "quant_portability_note",
        "INT4-AWQ checkpoints are portable across sm89/sm90+ GPUs; rebuild engines for the target GPU (e.g., H100/H200/B200/Blackwell, L40S, 4090/RTX)",
    )
    
    return metadata

