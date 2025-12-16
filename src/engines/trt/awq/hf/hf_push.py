#!/usr/bin/env python3
"""Push TRT-LLM quantized model to HuggingFace.

Usage:
    python -m src.engines.trt.awq.hf.hf_push \\
        --checkpoint-dir /path/to/checkpoints \\
        --engine-dir /path/to/engines \\
        --repo-id owner/model-name-trt-awq \\
        --token $HF_TOKEN
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .readme_renderer import render_trt_readme
from src.helpers.templates import compute_license_info


def push_trt_to_hf(
    checkpoint_dir: str,
    engine_dir: str,
    repo_id: str,
    token: str,
    *,
    branch: str = "main",
    base_model: str | None = None,
    quant_method: str = "int4_awq",
) -> bool:
    """Push TRT-LLM checkpoints and engines to HuggingFace.
    
    Args:
        checkpoint_dir: Path to TRT-LLM checkpoints directory.
        engine_dir: Path to TRT-LLM engines directory.
        repo_id: HuggingFace repo ID (owner/name).
        token: HuggingFace API token.
        branch: Branch to push to.
        base_model: Base model ID (auto-detected if not provided).
        quant_method: Quantization method (int4_awq, fp8, int8_sq).
        
    Returns:
        True if push succeeded, False otherwise.
    """
    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        print("[trt-hf] Error: huggingface_hub not installed")
        return False
    
    checkpoint_path = Path(checkpoint_dir)
    engine_path = Path(engine_dir)
    
    if not checkpoint_path.is_dir():
        print(f"[trt-hf] Error: Checkpoint directory not found: {checkpoint_dir}")
        return False
    
    # Detect base model from checkpoint config
    if not base_model:
        base_model = _detect_base_model(checkpoint_path)
    
    # Collect metadata for README
    metadata = _collect_metadata(checkpoint_path, engine_path, base_model, quant_method)
    
    # Render README
    readme_content = render_trt_readme(metadata)
    
    # Create staging directory
    staging_dir = Path(checkpoint_dir).parent / ".hf_staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    # Write README
    readme_path = staging_dir / "README.md"
    readme_path.write_text(readme_content, encoding="utf-8")
    
    # Create/get repo
    api = HfApi(token=token)
    try:
        create_repo(repo_id, token=token, exist_ok=True, repo_type="model")
    except Exception as e:
        print(f"[trt-hf] Warning: Could not create repo: {e}")
    
    # Upload README
    print(f"[trt-hf] Uploading README to {repo_id}")
    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id=repo_id,
        token=token,
        revision=branch,
    )
    
    # Upload checkpoints
    print(f"[trt-hf] Uploading checkpoints from {checkpoint_dir}")
    api.upload_folder(
        folder_path=str(checkpoint_path),
        path_in_repo="trt-llm/checkpoints",
        repo_id=repo_id,
        token=token,
        revision=branch,
    )
    
    # Upload engines if they exist
    if engine_path.is_dir():
        engine_label = _get_engine_label(engine_path)
        print(f"[trt-hf] Uploading engines from {engine_dir} as {engine_label}")
        api.upload_folder(
            folder_path=str(engine_path),
            path_in_repo=f"trt-llm/engines/{engine_label}",
            repo_id=repo_id,
            token=token,
            revision=branch,
        )
    
    print(f"[trt-hf] Successfully pushed to https://huggingface.co/{repo_id}")
    return True


def _detect_base_model(checkpoint_path: Path) -> str:
    """Detect base model from checkpoint config."""
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


def _get_engine_label(engine_path: Path) -> str:
    """Generate engine label from build metadata."""
    # Try to read build metadata
    meta_path = engine_path / "build_metadata.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            sm = meta.get("sm_arch", "sm89")
            trt_ver = meta.get("tensorrt_llm_version", "unknown")
            cuda_ver = meta.get("cuda_version", "unknown")
            return f"{sm}_trt-llm-{trt_ver}_cuda{cuda_ver}"
        except Exception:
            pass
    
    # Fallback: use directory name or generate from env
    sm = os.getenv("GPU_SM_ARCH", "sm89")
    return f"{sm}_default"


def _collect_metadata(
    checkpoint_path: Path,
    engine_path: Path,
    base_model: str,
    quant_method: str,
) -> dict[str, Any]:
    """Collect metadata for README rendering."""
    metadata = {
        "base_model": base_model,
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
    
    # Read checkpoint config
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
    
    # Engine metadata
    if engine_path.is_dir():
        metadata["engine_label"] = _get_engine_label(engine_path)
        meta_path = engine_path / "build_metadata.json"
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                metadata.update({
                    "sm_arch": meta.get("sm_arch", "unknown"),
                    "gpu_name": meta.get("gpu_name", "unknown"),
                    "cuda_toolkit": meta.get("cuda_version", "unknown"),
                    "tensorrt_llm_version": meta.get("tensorrt_llm_version", "unknown"),
                })
            except Exception:
                pass
    
    # Fetch license from the base model on HuggingFace
    # This ensures the quantized model inherits the correct license
    # Uses shared logic with vLLM AWQ push
    is_hf_model = "/" in base_model
    license_info = compute_license_info(base_model, is_tool=False, is_hf_model=is_hf_model)
    metadata.update(license_info)
    
    # Defaults
    metadata.setdefault("sm_arch", os.getenv("GPU_SM_ARCH", "sm89"))
    metadata.setdefault("gpu_name", "NVIDIA GPU")
    metadata.setdefault("cuda_toolkit", "12.0+")
    metadata.setdefault("tensorrt_llm_version", "0.17+")
    metadata.setdefault("engine_label", f"{metadata['sm_arch']}_default")
    metadata.setdefault("max_batch_size", "16")
    metadata.setdefault("max_input_len", "4096")
    metadata.setdefault("max_output_len", "512")
    metadata.setdefault("kv_cache_dtype", "fp8" if "fp8" in quant_method else "int8")
    metadata.setdefault("awq_block_size", "128")
    metadata.setdefault("calib_size", "64")
    metadata.setdefault("calib_seqlen", "2048")
    metadata.setdefault("calib_batch_size", "16")
    metadata.setdefault("min_compute_capability", "8.0")
    metadata.setdefault("gpu_arch_note", "A100/L40S/H100 or newer")
    metadata.setdefault("quant_portability_note", "INT4-AWQ models are portable across sm89/sm90+ GPUs")
    
    return metadata


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Push TRT-LLM model to HuggingFace")
    parser.add_argument("--checkpoint-dir", required=True, help="Path to TRT-LLM checkpoints")
    parser.add_argument("--engine-dir", default="", help="Path to TRT-LLM engines (optional)")
    parser.add_argument("--repo-id", required=True, help="HuggingFace repo ID (owner/name)")
    parser.add_argument("--token", required=True, help="HuggingFace API token")
    parser.add_argument("--branch", default="main", help="Branch to push to")
    parser.add_argument("--base-model", default="", help="Base model ID (auto-detected)")
    parser.add_argument("--quant-method", default="int4_awq", help="Quantization method")
    
    args = parser.parse_args()
    
    success = push_trt_to_hf(
        checkpoint_dir=args.checkpoint_dir,
        engine_dir=args.engine_dir or "",
        repo_id=args.repo_id,
        token=args.token,
        branch=args.branch,
        base_model=args.base_model or None,
        quant_method=args.quant_method,
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

