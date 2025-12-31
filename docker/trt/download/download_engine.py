#!/usr/bin/env python3
"""Download pre-built TRT engine from HuggingFace at Docker build time."""

import os
import shutil
import sys


def download_engine(repo_id: str, engine_label: str, target_dir: str, token: str | None = None) -> None:
    """Download TRT engine files from HuggingFace.
    
    Downloads from: {repo_id}/trt-llm/engines/{engine_label}/
    Places files in: {target_dir}/
    
    Args:
        repo_id: HuggingFace repo ID containing pre-built engines
        engine_label: Engine directory name (e.g., sm90_trt-llm-0.17.0_cuda12.8)
        target_dir: Local directory to store engine files
        token: Optional HuggingFace token for private repos
    """
    from huggingface_hub import snapshot_download

    print(f"[build] Downloading TRT engine from {repo_id}...")
    print(f"[build]   Engine label: {engine_label}")
    print(f"[build]   Target: {target_dir}")

    # Download engine files from nested structure
    snapshot_download(
        repo_id=repo_id,
        local_dir=target_dir,
        allow_patterns=[f"trt-llm/engines/{engine_label}/**"],
        token=token,
    )

    # Move files from nested structure to target dir
    nested_dir = os.path.join(target_dir, "trt-llm", "engines", engine_label)
    if os.path.isdir(nested_dir):
        for f in os.listdir(nested_dir):
            src = os.path.join(nested_dir, f)
            dst = os.path.join(target_dir, f)
            shutil.move(src, dst)
        # Clean up nested directories
        shutil.rmtree(os.path.join(target_dir, "trt-llm"))

    # Verify engine files exist
    engine_files = [f for f in os.listdir(target_dir) if f.endswith(".engine")]
    if not engine_files:
        print(f"[build] ERROR: No .engine files found in {target_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[build] ✓ Downloaded {len(engine_files)} engine file(s)")


def main() -> None:
    repo_id = os.environ.get("TRT_ENGINE_REPO", "")
    engine_label = os.environ.get("TRT_ENGINE_LABEL", "")
    target_dir = os.environ.get("TRT_ENGINE_DIR", "/opt/engines/trt-chat")
    
    # Token from env or mounted secret
    token = os.environ.get("HF_TOKEN") or None
    if not token:
        secret_path = "/run/secrets/hf_token"
        if os.path.isfile(secret_path):
            with open(secret_path) as f:
                token = f.read().strip() or None

    if not repo_id or not engine_label:
        print("[build] No TRT_ENGINE_REPO/TRT_ENGINE_LABEL set - skipping engine download")
        return

    try:
        download_engine(repo_id, engine_label, target_dir, token)
        print("[build] ✓ TRT engine baked into image")
    except Exception as e:
        print(f"[build] ERROR: Failed to download engine: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

