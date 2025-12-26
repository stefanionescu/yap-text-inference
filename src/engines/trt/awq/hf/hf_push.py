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
import sys
from pathlib import Path

from ..core.metadata import collect_metadata, detect_base_model, get_engine_label
from .readme_renderer import render_trt_readme


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
        base_model = detect_base_model(checkpoint_path)
    
    # Collect metadata for README
    metadata = collect_metadata(checkpoint_path, engine_path, base_model, repo_id, quant_method)
    
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
        engine_label = get_engine_label(engine_path)
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
