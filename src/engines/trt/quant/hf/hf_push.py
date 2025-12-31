#!/usr/bin/env python3
"""Push TRT-LLM quantized model to HuggingFace.

This module handles uploading TRT-LLM checkpoints and engines to HuggingFace Hub.
It supports both full uploads (checkpoint + engine + tokenizer) and engine-only
uploads to existing repositories.

Upload Structure:
    repo/
    ├── README.md                    # Auto-generated model card
    ├── tokenizer.json               # Tokenizer files (from checkpoint or base model)
    ├── tokenizer_config.json
    ├── chat_template.jinja          # Optional chat template
    ├── trt-llm/
    │   ├── checkpoints/             # Quantized checkpoint files
    │   └── engines/{label}/         # Pre-built TRT engines by GPU

Usage:
    python -m src.engines.trt.quant.hf.hf_push push \\
        --checkpoint-dir /path/to/checkpoints \\
        --engine-dir /path/to/engines \\
        --repo-id owner/model-name-trt-awq \\
        --token $HF_TOKEN
    
    python -m src.engines.trt.quant.hf.hf_push push-engine \\
        --engine-dir /path/to/engines \\
        --repo-id owner/existing-repo \\
        --token $HF_TOKEN
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from src.helpers.env import env_flag

# Conditionally apply log filter based on SHOW_HF_LOGS
if not env_flag("SHOW_HF_LOGS", False):
    import src.scripts.log_filter  # noqa: F401 - suppress HF progress bars

from src.config.quantization import CHAT_TEMPLATE_FILES, TOKENIZER_FILES
from ..metadata import collect_metadata, detect_base_model, get_engine_label
from .readme_renderer import render_trt_readme

if TYPE_CHECKING:
    from huggingface_hub import HfApi

__all__ = ["push_trt_to_hf", "push_engine_to_hf"]


# ============================================================================
# Constants
# ============================================================================

_HF_CHECKPOINTS_PATH = "trt-llm/checkpoints"
_HF_ENGINES_PATH_FMT = "trt-llm/engines/{engine_label}"
_TOKENIZER_CONFIG = "tokenizer_config.json"
_CHECKPOINT_SUFFIXES = ("-int4_awq-ckpt", "-fp8-ckpt", "-int8_sq-ckpt", "-ckpt")


# ============================================================================
# HuggingFace API Helpers
# ============================================================================

def _get_hf_api(token: str) -> "HfApi | None":
    """Get HfApi instance, returning None if huggingface_hub is not installed."""
    try:
        from huggingface_hub import HfApi
        return HfApi(token=token)
    except ImportError:
        print("[trt-hf] Error: huggingface_hub not installed")
        return None


def _create_repo_if_needed(
    api: "HfApi",
    repo_id: str,
    token: str,
    private: bool,
) -> None:
    """Create repository if it doesn't exist."""
    try:
        from huggingface_hub import create_repo
        create_repo(repo_id, token=token, exist_ok=True, repo_type="model", private=private)
    except Exception as e:
        print(f"[trt-hf] Warning: Could not create repo: {e}")


def _verify_repo_exists(api: "HfApi", repo_id: str, token: str) -> bool:
    """Verify that a repository exists and is accessible."""
    try:
        api.repo_info(repo_id=repo_id, token=token)
        return True
    except Exception as e:
        print(f"[trt-hf] Error: Repository {repo_id} not found or not accessible: {e}")
        print("[trt-hf]   Use 'push' command to create a new repo with checkpoint + engine")
        return False


# ============================================================================
# Tokenizer Discovery
# ============================================================================

def _has_tokenizer(directory: Path) -> bool:
    """Check if a directory contains a tokenizer config."""
    return (directory / _TOKENIZER_CONFIG).exists()


def _extract_model_stem(checkpoint_name: str) -> str:
    """Extract model stem by removing known checkpoint suffixes."""
    for suffix in _CHECKPOINT_SUFFIXES:
        if checkpoint_name.endswith(suffix):
            return checkpoint_name[: -len(suffix)]
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
        import tempfile
        from huggingface_hub import snapshot_download

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
    if result := _find_hf_dir_in_path(checkpoint_dir.parent, model_stem):
        return result

    # Check workspace models/ directory
    workspace_models = checkpoint_dir.parent.parent / "models"
    if workspace_models.is_dir():
        if result := _find_hf_dir_in_path(workspace_models, model_stem):
            return result

    # Download from HuggingFace as last resort
    if base_model:
        return _download_tokenizer_from_hub(base_model)

    return None


# ============================================================================
# Upload Helpers
# ============================================================================

def _upload_file(
    api: "HfApi",
    src: Path,
    dest: str,
    repo_id: str,
    token: str,
    branch: str,
) -> bool:
    """Upload a single file to HuggingFace. Returns True on success."""
    try:
        api.upload_file(
            path_or_fileobj=str(src),
            path_in_repo=dest,
            repo_id=repo_id,
            token=token,
            revision=branch,
        )
        return True
    except Exception as exc:
        print(f"[trt-hf] Warning: Failed to upload {dest}: {exc}")
        return False


def _upload_readme(
    api: "HfApi",
    metadata: dict,
    staging_dir: Path,
    repo_id: str,
    token: str,
    branch: str,
) -> None:
    """Render and upload README.md."""
    readme_content = render_trt_readme(metadata)
    readme_path = staging_dir / "README.md"
    readme_path.write_text(readme_content, encoding="utf-8")
    _upload_file(api, readme_path, "README.md", repo_id, token, branch)


def _upload_checkpoint(
    api: "HfApi",
    checkpoint_path: Path,
    repo_id: str,
    token: str,
    branch: str,
) -> None:
    """Upload checkpoint folder."""
    print("[trt-hf] Uploading checkpoint...")
    api.upload_folder(
        folder_path=str(checkpoint_path),
        path_in_repo=_HF_CHECKPOINTS_PATH,
        repo_id=repo_id,
        token=token,
        revision=branch,
    )


def _upload_engine(
    api: "HfApi",
    engine_path: Path,
    repo_id: str,
    token: str,
    branch: str,
) -> bool:
    """Upload engine folder. Returns True on success."""
    if not engine_path.is_dir():
        return False

    engine_label = get_engine_label(engine_path)
    engines_path = _HF_ENGINES_PATH_FMT.format(engine_label=engine_label)
    print("[trt-hf] Uploading engines...")

    try:
        api.upload_folder(
            folder_path=str(engine_path),
            path_in_repo=engines_path,
            repo_id=repo_id,
            token=token,
            revision=branch,
        )
        return True
    except Exception as e:
        print(f"[trt-hf] Error: Failed to upload engine: {e}")
        return False


def _upload_tokenizer(
    api: "HfApi",
    tokenizer_dir: Path | None,
    repo_id: str,
    token: str,
    branch: str,
) -> None:
    """Upload tokenizer files if found."""
    if not tokenizer_dir:
        print("[trt-hf] Warning: Tokenizer not found; TRT-LLM will download from base model at runtime")
        return

    print("[trt-hf] Uploading tokenizer...")
    for filename in TOKENIZER_FILES:
        src_file = tokenizer_dir / filename
        if src_file.exists():
            _upload_file(api, src_file, filename, repo_id, token, branch)


def _upload_chat_assets(
    api: "HfApi",
    candidate_dirs: list[Path],
    repo_id: str,
    token: str,
    branch: str,
) -> None:
    """Upload chat template and generation config if present."""
    uploaded = 0
    tried_dirs: set[Path] = set()

    for directory in candidate_dirs:
        if not directory or directory in tried_dirs:
            continue
        tried_dirs.add(directory)

        for filename in CHAT_TEMPLATE_FILES:
            src = directory / filename
            if src.exists() and _upload_file(api, src, filename, repo_id, token, branch):
                uploaded += 1

    if uploaded > 0:
        print("[trt-hf] ✓ Uploaded chat template assets")
    else:
        print("[trt-hf] No chat template/generation_config files found. Skipping")


# ============================================================================
# Core Push Functions
# ============================================================================

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
    api = _get_hf_api(token)
    if api is None:
        return False

    checkpoint_path = Path(checkpoint_dir)
    engine_path = Path(engine_dir)

    if not checkpoint_path.is_dir():
        print(f"[trt-hf] Error: Checkpoint directory not found: {checkpoint_dir}")
        return False

    # Detect base model from checkpoint config
    resolved_base_model = base_model or detect_base_model(checkpoint_path)

    # Collect metadata and prepare staging
    metadata = collect_metadata(
        checkpoint_path, engine_path, resolved_base_model, repo_id, quant_method
    )
    staging_dir = checkpoint_path.parent / ".hf_staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    # Create repo and upload artifacts
    _create_repo_if_needed(api, repo_id, token, private)
    _upload_readme(api, metadata, staging_dir, repo_id, token, branch)
    _upload_checkpoint(api, checkpoint_path, repo_id, token, branch)
    _upload_engine(api, engine_path, repo_id, token, branch)

    # Upload tokenizer and chat assets
    tokenizer_dir = _find_tokenizer_dir(checkpoint_path, resolved_base_model)
    _upload_tokenizer(api, tokenizer_dir, repo_id, token, branch)

    chat_asset_dirs = [d for d in [tokenizer_dir, checkpoint_path] if d]
    _upload_chat_assets(api, chat_asset_dirs, repo_id, token, branch)

    print(f"[trt-hf] ✓ Push complete: {repo_id}")
    return True


def push_engine_to_hf(
    engine_dir: str,
    repo_id: str,
    token: str,
    *,
    branch: str = "main",
) -> bool:
    """Push only a TRT-LLM engine to an existing HuggingFace repository.

    Use this when building an engine locally for a pre-quantized model
    and wanting to add the engine without modifying checkpoint or other files.

    Args:
        engine_dir: Path to TRT-LLM engines directory.
        repo_id: HuggingFace repo ID (owner/name) - must already exist.
        token: HuggingFace API token.
        branch: Branch to push to.

    Returns:
        True if push succeeded, False otherwise.
    """
    api = _get_hf_api(token)
    if api is None:
        return False

    engine_path = Path(engine_dir)

    # Validate engine directory
    if not engine_path.is_dir():
        print(f"[trt-hf] Error: Engine directory not found: {engine_dir}")
        return False

    engine_files = list(engine_path.glob("rank*.engine"))
    if not engine_files:
        print(f"[trt-hf] Error: No rank*.engine files found in {engine_dir}")
        return False

    # Get engine label
    try:
        engine_label = get_engine_label(engine_path)
    except Exception as e:
        print(f"[trt-hf] Error: Could not determine engine label: {e}")
        return False

    # Verify repo exists
    if not _verify_repo_exists(api, repo_id, token):
        return False

    # Upload engine
    engines_path = _HF_ENGINES_PATH_FMT.format(engine_label=engine_label)
    print("[trt-hf] Uploading engine...")

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


# ============================================================================
# CLI
# ============================================================================

def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments common to all push commands."""
    parser.add_argument("--repo-id", required=True, help="HuggingFace repo ID (owner/name)")
    parser.add_argument("--token", required=True, help="HuggingFace API token")
    parser.add_argument("--branch", default="main", help="Branch to push to")


def _add_full_push_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments for full checkpoint+engine push."""
    parser.add_argument("--checkpoint-dir", required=True, help="Path to TRT-LLM checkpoints")
    parser.add_argument("--engine-dir", default="", help="Path to TRT-LLM engines (optional)")
    parser.add_argument("--base-model", default="", help="Base model ID (auto-detected)")
    parser.add_argument("--quant-method", default="int4_awq", help="Quantization method")
    parser.add_argument("--private", action="store_true", help="Create private repo")


def _run_full_push(args: argparse.Namespace) -> int:
    """Execute full push with checkpoint and optional engine."""
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


def _run_engine_push(args: argparse.Namespace) -> int:
    """Execute engine-only push."""
    success = push_engine_to_hf(
        engine_dir=args.engine_dir,
        repo_id=args.repo_id,
        token=args.token,
        branch=args.branch,
    )
    return 0 if success else 1


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Push TRT-LLM model to HuggingFace")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Full push: checkpoint + engine
    push_parser = subparsers.add_parser("push", help="Push checkpoint and engine")
    _add_common_args(push_parser)
    _add_full_push_args(push_parser)

    # Engine-only push
    engine_parser = subparsers.add_parser("push-engine", help="Push only engine to existing repo")
    engine_parser.add_argument("--engine-dir", required=True, help="Path to TRT-LLM engines")
    _add_common_args(engine_parser)

    args = parser.parse_args()

    if args.command == "push":
        return _run_full_push(args)
    if args.command == "push-engine":
        return _run_engine_push(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
