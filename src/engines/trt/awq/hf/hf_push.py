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

from src.helpers.env import env_flag

# Conditionally apply log filter based on SHOW_HF_LOGS
if not env_flag("SHOW_HF_LOGS", False):
    import src.scripts.log_filter  # noqa: F401 - suppress HF progress bars

from src.config.quantization import CHAT_TEMPLATE_FILES, TOKENIZER_FILES
from ..core.metadata import collect_metadata, detect_base_model, get_engine_label
from .readme_renderer import render_trt_readme

# HuggingFace repo path prefixes for TRT-LLM artifacts
_HF_CHECKPOINTS_PATH = "trt-llm/checkpoints"
_HF_ENGINES_PATH_FMT = "trt-llm/engines/{engine_label}"


_TOKENIZER_CONFIG = "tokenizer_config.json"
_CHECKPOINT_SUFFIXES = ("-int4_awq-ckpt", "-fp8-ckpt", "-int8_sq-ckpt", "-ckpt")


def _has_tokenizer(directory: Path) -> bool:
    """Check if a directory contains a tokenizer config."""
    return (directory / _TOKENIZER_CONFIG).exists()


def _extract_model_stem(checkpoint_name: str) -> str:
    """Extract model stem by removing known checkpoint suffixes."""
    for suffix in _CHECKPOINT_SUFFIXES:
        if checkpoint_name.endswith(suffix):
            return checkpoint_name[:-len(suffix)]
    return checkpoint_name


def _find_hf_dir_in_path(parent: Path, model_stem: str) -> Path | None:
    """Look for a {model_stem}-hf directory with tokenizer."""
    hf_dir = parent / f"{model_stem}-hf"
    if hf_dir.is_dir() and _has_tokenizer(hf_dir):
        return hf_dir
    return None


def _download_tokenizer_from_hub(base_model: str) -> Path | None:
    """Download tokenizer files from HuggingFace hub to temp dir."""
    try:
        from huggingface_hub import snapshot_download
        import tempfile
        
        temp_dir = Path(tempfile.mkdtemp(prefix="tokenizer_"))
        snapshot_download(
            repo_id=base_model,
            local_dir=str(temp_dir),
            allow_patterns=list(TOKENIZER_FILES),
        )
        if _has_tokenizer(temp_dir):
            return temp_dir
    except Exception as e:
        print(f"[trt-hf] Warning: Failed to download tokenizer from {base_model}: {e}")
    return None


def _find_tokenizer_dir(checkpoint_dir: Path, base_model: str | None) -> Path | None:
    """Find directory containing tokenizer files.
    
    Search order:
    1. Checkpoint directory itself
    2. Sibling {model_stem}-hf directory
    3. models/{model_stem}-hf in workspace root
    4. Download from HuggingFace if base_model provided
    """
    if _has_tokenizer(checkpoint_dir):
        return checkpoint_dir
    
    model_stem = _extract_model_stem(checkpoint_dir.name)
    
    # Check sibling -hf directory
    result = _find_hf_dir_in_path(checkpoint_dir.parent, model_stem)
    if result:
        return result
    
    # Check workspace models/ directory
    workspace_models = checkpoint_dir.parent.parent / "models"
    if workspace_models.is_dir():
        result = _find_hf_dir_in_path(workspace_models, model_stem)
        if result:
            return result
    
    # Download from HuggingFace as last resort
    if base_model:
        return _download_tokenizer_from_hub(base_model)
    
    return None


def _upload_chat_assets(
    api,
    *,
    repo_id: str,
    branch: str,
    token: str,
    candidate_dirs: list[Path],
) -> None:
    """Upload chat template and generation config if present in any candidate dir."""
    uploaded = 0
    tried_dirs: set[Path] = set()

    for directory in candidate_dirs:
        if not directory or directory in tried_dirs:
            continue
        tried_dirs.add(directory)
        for filename in CHAT_TEMPLATE_FILES:
            src = directory / filename
            if not src.exists():
                continue
            try:
                api.upload_file(
                    path_or_fileobj=str(src),
                    path_in_repo=filename,
                    repo_id=repo_id,
                    token=token,
                    revision=branch,
                )
                uploaded += 1
            except Exception as exc:
                print(f"[trt-hf] Warning: failed to upload {filename} from {src}: {exc}")

    if uploaded > 0:
        print(f"[trt-hf] ✓ Uploaded chat template assets")
    else:
        print("[trt-hf] No chat template/generation_config files found. Skipping")


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
    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id=repo_id,
        token=token,
        revision=branch,
    )
    
    # Upload checkpoints
    print(f"[trt-hf] Uploading checkpoint...")
    api.upload_folder(
        folder_path=str(checkpoint_path),
        path_in_repo=_HF_CHECKPOINTS_PATH,
        repo_id=repo_id,
        token=token,
        revision=branch,
    )
    
    # Upload engines if they exist
    if engine_path.is_dir():
        engine_label = get_engine_label(engine_path)
        engines_path = _HF_ENGINES_PATH_FMT.format(engine_label=engine_label)
        print(f"[trt-hf] Uploading engines...")
        api.upload_folder(
            folder_path=str(engine_path),
            path_in_repo=engines_path,
            repo_id=repo_id,
            token=token,
            revision=branch,
        )
    
    # Upload tokenizer files (required for TRT-LLM to load the model)
    tokenizer_dir = _find_tokenizer_dir(checkpoint_path, base_model)
    if tokenizer_dir:
        print(f"[trt-hf] Uploading tokenizer...")
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
    else:
        print("[trt-hf] Warning: Could not find tokenizer directory; tokenizer not uploaded")
        print("[trt-hf]   TRT-LLM will need to download tokenizer from base model at runtime")

    # Upload chat template + generation config if available
    chat_asset_dirs: list[Path] = []
    if tokenizer_dir:
        chat_asset_dirs.append(tokenizer_dir)
    chat_asset_dirs.append(checkpoint_path)
    _upload_chat_assets(
        api,
        repo_id=repo_id,
        branch=branch,
        token=token,
        candidate_dirs=chat_asset_dirs,
    )
    
    return True


def push_engine_to_hf(
    engine_dir: str,
    repo_id: str,
    token: str,
    *,
    branch: str = "main",
) -> bool:
    """Push only a TRT-LLM engine to an existing HuggingFace repository.
    
    This is used when building an engine locally for a pre-quantized model
    and wanting to add the engine to the existing repo without modifying
    the checkpoint or other files.
    
    Args:
        engine_dir: Path to TRT-LLM engines directory.
        repo_id: HuggingFace repo ID (owner/name) - must already exist.
        token: HuggingFace API token.
        branch: Branch to push to.
        
    Returns:
        True if push succeeded, False otherwise.
    """
    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("[trt-hf] Error: huggingface_hub not installed")
        return False
    
    engine_path = Path(engine_dir)
    
    if not engine_path.is_dir():
        print(f"[trt-hf] Error: Engine directory not found: {engine_dir}")
        return False
    
    # Validate engine files exist
    engine_files = list(engine_path.glob("rank*.engine"))
    if not engine_files:
        print(f"[trt-hf] Error: No rank*.engine files found in {engine_dir}")
        return False
    
    # Get engine label from metadata or environment
    try:
        engine_label = get_engine_label(engine_path)
    except Exception as e:
        print(f"[trt-hf] Error: Could not determine engine label: {e}")
        return False
    
    api = HfApi(token=token)
    
    # Verify repo exists
    try:
        api.repo_info(repo_id=repo_id, token=token)
    except Exception as e:
        print(f"[trt-hf] Error: Repository {repo_id} not found or not accessible: {e}")
        print("[trt-hf]   Use --push-quant to create a new repo with checkpoint + engine")
        return False
    
    # Upload engine to engines/{engine_label}/
    engines_path = _HF_ENGINES_PATH_FMT.format(engine_label=engine_label)
    print(f"[trt-hf] Uploading engine...")
    try:
        api.upload_folder(
            folder_path=str(engine_path),
            path_in_repo=engines_path,
            repo_id=repo_id,
            token=token,
            revision=branch,
        )
    except Exception as e:
        print(f"[trt-hf] Error: Failed to upload engine: {e}")
        return False
    
    print(f"[trt-hf] ✓ Engine uploaded to {repo_id}")
    print(f"[trt-hf]   Path: {engines_path}")
    return True


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Push TRT-LLM model to HuggingFace")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Default push command (full push with checkpoint + engine)
    push_parser = subparsers.add_parser("push", help="Push checkpoint and engine")
    push_parser.add_argument("--checkpoint-dir", required=True, help="Path to TRT-LLM checkpoints")
    push_parser.add_argument("--engine-dir", default="", help="Path to TRT-LLM engines (optional)")
    push_parser.add_argument("--repo-id", required=True, help="HuggingFace repo ID (owner/name)")
    push_parser.add_argument("--token", required=True, help="HuggingFace API token")
    push_parser.add_argument("--branch", default="main", help="Branch to push to")
    push_parser.add_argument("--base-model", default="", help="Base model ID (auto-detected)")
    push_parser.add_argument("--quant-method", default="int4_awq", help="Quantization method")
    push_parser.add_argument("--private", action="store_true", help="Create repo as private if it doesn't exist")
    
    # Engine-only push command
    engine_parser = subparsers.add_parser("push-engine", help="Push only engine to existing repo")
    engine_parser.add_argument("--engine-dir", required=True, help="Path to TRT-LLM engines")
    engine_parser.add_argument("--repo-id", required=True, help="HuggingFace repo ID (owner/name)")
    engine_parser.add_argument("--token", required=True, help="HuggingFace API token")
    engine_parser.add_argument("--branch", default="main", help="Branch to push to")
    
    # For backwards compatibility, also support the old CLI format without subcommand
    parser.add_argument("--checkpoint-dir", default="", help="Path to TRT-LLM checkpoints")
    parser.add_argument("--engine-dir", default="", help="Path to TRT-LLM engines")
    parser.add_argument("--repo-id", default="", help="HuggingFace repo ID (owner/name)")
    parser.add_argument("--token", default="", help="HuggingFace API token")
    parser.add_argument("--branch", default="main", help="Branch to push to")
    parser.add_argument("--base-model", default="", help="Base model ID (auto-detected)")
    parser.add_argument("--quant-method", default="int4_awq", help="Quantization method")
    parser.add_argument("--private", action="store_true", help="Create repo as private if it doesn't exist")
    parser.add_argument("--engine-only", action="store_true", help="Push only engine to existing repo")
    
    args = parser.parse_args()
    
    # Handle subcommand-based invocation
    if args.command == "push":
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
    elif args.command == "push-engine":
        success = push_engine_to_hf(
            engine_dir=args.engine_dir,
            repo_id=args.repo_id,
            token=args.token,
            branch=args.branch,
        )
        return 0 if success else 1
    
    # Handle legacy CLI format (no subcommand)
    if args.engine_only:
        if not args.engine_dir or not args.repo_id or not args.token:
            print("[trt-hf] Error: --engine-only requires --engine-dir, --repo-id, and --token")
            return 1
        success = push_engine_to_hf(
            engine_dir=args.engine_dir,
            repo_id=args.repo_id,
            token=args.token,
            branch=args.branch,
        )
        return 0 if success else 1
    
    # Standard full push
    if not args.checkpoint_dir or not args.repo_id or not args.token:
        parser.print_help()
        return 1
    
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
