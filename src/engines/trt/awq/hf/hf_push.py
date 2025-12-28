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

from src.config.quantization import TOKENIZER_FILES
from ..core.metadata import collect_metadata, detect_base_model, get_engine_label
from .readme_renderer import render_trt_readme


def _find_tokenizer_dir(checkpoint_dir: Path, base_model: str | None) -> Path | None:
    """Find directory containing tokenizer files.
    
    Checks:
    1. Checkpoint directory itself
    2. Parent's HF download (model-hf directory)
    3. Downloads from HuggingFace if base_model provided
    """
    # Check if tokenizer is in checkpoint dir
    if (checkpoint_dir / "tokenizer_config.json").exists():
        return checkpoint_dir
    
    # Check sibling -hf directory (where model was downloaded)
    # e.g., /models/foo-int4_awq-ckpt -> /models/foo-hf
    ckpt_name = checkpoint_dir.name
    for suffix in ["-int4_awq-ckpt", "-fp8-ckpt", "-int8_sq-ckpt", "-ckpt"]:
        if ckpt_name.endswith(suffix):
            hf_dir = checkpoint_dir.parent / (ckpt_name.replace(suffix, "-hf"))
            if hf_dir.is_dir() and (hf_dir / "tokenizer_config.json").exists():
                return hf_dir
            break
    
    # Try to find in parent models directory
    models_dir = checkpoint_dir.parent
    for subdir in models_dir.iterdir():
        if subdir.is_dir() and subdir.name.endswith("-hf"):
            if (subdir / "tokenizer_config.json").exists():
                return subdir
    
    return None


def push_trt_to_hf(
    checkpoint_dir: str,
    engine_dir: str,
    repo_id: str,
    token: str,
    *,
    branch: str = "main",
    base_model: str | None = None,
    quant_method: str = "int4_awq",
    private: bool = False,
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
        private: Create repo as private if it doesn't exist.
        
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
        create_repo(repo_id, token=token, exist_ok=True, repo_type="model", private=private)
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
    
    # Upload tokenizer files (required for TRT-LLM to load the model)
    tokenizer_dir = _find_tokenizer_dir(checkpoint_path, base_model)
    if tokenizer_dir:
        print(f"[trt-hf] Uploading tokenizer from {tokenizer_dir}")
        tokenizer_files_found = 0
        for filename in TOKENIZER_FILES:
            src_file = tokenizer_dir / filename
            if src_file.exists():
                api.upload_file(
                    path_or_fileobj=str(src_file),
                    path_in_repo=filename,
                    repo_id=repo_id,
                    token=token,
                    revision=branch,
                )
                tokenizer_files_found += 1
        if tokenizer_files_found > 0:
            print(f"[trt-hf] Uploaded {tokenizer_files_found} tokenizer files")
        else:
            print("[trt-hf] Warning: No tokenizer files found to upload")
    else:
        print("[trt-hf] Warning: Could not find tokenizer directory; tokenizer not uploaded")
        print("[trt-hf]   TRT-LLM will need to download tokenizer from base model at runtime")
    
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
    parser.add_argument("--private", action="store_true", help="Create repo as private if it doesn't exist")
    
    args = parser.parse_args()
    
    success = push_trt_to_hf(
        checkpoint_dir=args.checkpoint_dir,
        engine_dir=args.engine_dir or "",
        repo_id=args.repo_id,
        token=args.token,
        branch=args.branch,
        base_model=args.base_model or None,
        quant_method=args.quant_method,
        private=args.private,
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
