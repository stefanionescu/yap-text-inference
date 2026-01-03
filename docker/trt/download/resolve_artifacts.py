#!/usr/bin/env python3
"""Resolve and download TRT artifacts from HuggingFace at runtime.

This module handles runtime artifact resolution for TRT engines, including:
- Engine directory selection based on GPU SM architecture
- Checkpoint fallback when no matching engine is found
- Build metadata validation

Used by start_server.sh when the image was built without baked-in engines
or when additional runtime downloads are needed.
"""

import os
import sys
from pathlib import Path


def get_repo_files(repo_id: str, token: str | None = None) -> list[str]:
    """List all files in a HuggingFace repo."""
    from huggingface_hub import list_repo_tree
    
    files = list(list_repo_tree(repo_id, token=token))
    return [f.path for f in files]


def find_engine_labels(paths: list[str]) -> set[str]:
    """Extract engine label directories from repo paths."""
    labels = set()
    for p in paths:
        if p.startswith("trt-llm/engines/"):
            parts = p.split("/")
            if len(parts) >= 4:
                labels.add(parts[3])
    return labels


def select_engine_label(
    engine_labels: set[str],
    preferred_label: str | None = None,
    gpu_sm: str | None = None,
) -> str | None:
    """Select the best matching engine label.
    
    Priority:
        1. Exact match to preferred_label
        2. Single available label
        3. Label matching GPU SM architecture
    """
    if not engine_labels:
        return None
    
    # Exact match
    if preferred_label and preferred_label in engine_labels:
        return preferred_label
    
    # Single available
    if len(engine_labels) == 1:
        return next(iter(engine_labels))
    
    # SM arch match
    if gpu_sm:
        matches = [lab for lab in sorted(engine_labels) if lab.startswith(gpu_sm)]
        if len(matches) == 1:
            return matches[0]
    
    return None


def download_engine(
    repo_id: str,
    engine_label: str,
    target_dir: str,
    token: str | None = None,
) -> str:
    """Download TRT engine files from HuggingFace.
    
    Returns path to the engine directory.
    """
    from huggingface_hub import snapshot_download
    
    local = snapshot_download(
        repo_id=repo_id,
        local_dir=target_dir,
        allow_patterns=[
            f"trt-llm/engines/{engine_label}/**",
            "trt-llm/engines/**/build_metadata.json",
        ],
        token=token,
    )
    
    return str(Path(local) / "trt-llm" / "engines" / engine_label)


def download_checkpoint(
    repo_id: str,
    target_dir: str,
    token: str | None = None,
) -> str:
    """Download TRT checkpoint files from HuggingFace.
    
    Returns path to the checkpoint directory.
    """
    from huggingface_hub import snapshot_download
    
    local = snapshot_download(
        repo_id=repo_id,
        local_dir=target_dir,
        allow_patterns=["trt-llm/checkpoints/**"],
        token=token,
    )
    
    return str(Path(local) / "trt-llm" / "checkpoints")


def get_hf_token() -> str | None:
    """Get HuggingFace token from environment or mounted secret."""
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN") or None
    if token:
        return token
    
    secret_path = "/run/secrets/hf_token"
    if os.path.isfile(secret_path):
        with open(secret_path) as f:
            token = f.read().strip() or None
    
    return token


def main() -> None:
    """Resolve TRT artifacts and output results for shell consumption."""
    # Suppress HF logs unless explicitly enabled
    show_hf_logs = os.environ.get("SHOW_HF_LOGS", "0").lower() in ("1", "true", "yes")
    if not show_hf_logs:
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    
    repo_id = os.environ.get("TRT_ENGINE_REPO", "").strip()
    engine_dir = os.environ.get("TRT_ENGINE_DIR", "/opt/engines/trt-chat")
    gpu_sm = os.environ.get("GPU_SM", "").strip()
    engine_label = os.environ.get("TRT_ENGINE_LABEL", "").strip()
    token = get_hf_token()
    
    if not repo_id:
        print("MODE=none")
        return
    
    try:
        paths = get_repo_files(repo_id, token)
    except Exception as e:
        print(f"ERROR=Failed to list repo: {e}", file=sys.stderr)
        print("MODE=error")
        sys.exit(1)
    
    # Try to find and download engine
    engine_labels = find_engine_labels(paths)
    selected = select_engine_label(engine_labels, engine_label, gpu_sm)
    
    if selected:
        try:
            eng_dir = download_engine(repo_id, selected, engine_dir, token)
            print("MODE=engines")
            print(f"ENGINE_DIR={eng_dir}")
            print(f"ENGINE_LABEL={selected}")
            return
        except Exception as e:
            print(f"ERROR=Engine download failed: {e}", file=sys.stderr)
    
    # Fallback to checkpoints
    has_checkpoints = any(p.startswith("trt-llm/checkpoints/") for p in paths)
    if has_checkpoints:
        try:
            ckpt_dir = download_checkpoint(repo_id, engine_dir, token)
            if (Path(ckpt_dir) / "config.json").is_file():
                print("MODE=checkpoints")
                print(f"CHECKPOINT_DIR={ckpt_dir}")
                return
        except Exception as e:
            print(f"ERROR=Checkpoint download failed: {e}", file=sys.stderr)
    
    print("MODE=none")


if __name__ == "__main__":
    main()
