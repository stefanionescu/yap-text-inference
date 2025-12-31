#!/usr/bin/env python3
"""Download tool classifier model from HuggingFace at Docker build time.

This shared module is used by both TRT and vLLM Docker builds to download the
tool classifier model. The tool model is a PyTorch model that runs on both
engines without engine-specific compilation.
"""

import os
import sys


def download_tool_model(repo_id: str, target_dir: str, token: str | None = None) -> None:
    """Download complete tool classifier model from HuggingFace.
    
    Args:
        repo_id: HuggingFace repo ID for the tool model
        target_dir: Local directory to store model files
        token: Optional HuggingFace token for private repos
    """
    from huggingface_hub import snapshot_download

    print(f"[build] Downloading tool model from {repo_id}...")
    print(f"[build]   Target: {target_dir}")

    os.makedirs(target_dir, exist_ok=True)

    snapshot_download(
        repo_id=repo_id,
        local_dir=target_dir,
        token=token,
    )

    print("[build] ✓ Tool model downloaded and baked into image")


def main() -> None:
    repo_id = os.environ.get("TOOL_MODEL", "")
    target_dir = os.environ.get("TOOL_MODEL_PATH", "/opt/models/tool")

    # Token from env or mounted secret
    token = os.environ.get("HF_TOKEN") or None
    if not token:
        secret_path = "/run/secrets/hf_token"
        if os.path.isfile(secret_path):
            with open(secret_path) as f:
                token = f.read().strip() or None

    if not repo_id:
        print("[build] No TOOL_MODEL specified - skipping tool model download")
        return

    try:
        download_tool_model(repo_id, target_dir, token)
    except Exception as e:
        print(f"[build] ERROR: Failed to download tool model: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

