#!/usr/bin/env python3
"""Download pre-quantized chat model from HuggingFace at Docker build time."""

import os
import sys


def download_chat_model(repo_id: str, target_dir: str, token: str | None = None) -> None:
    """Download complete chat model from HuggingFace.
    
    Args:
        repo_id: HuggingFace repo ID for the chat model
        target_dir: Local directory to store model files
        token: Optional HuggingFace token for private repos
    """
    from huggingface_hub import snapshot_download

    print(f"[build] Downloading chat model from {repo_id}...")
    print(f"[build]   Target: {target_dir}")

    os.makedirs(target_dir, exist_ok=True)

    snapshot_download(
        repo_id=repo_id,
        local_dir=target_dir,
        token=token,
    )

    print("[build] ✓ Chat model downloaded and baked into image")


def main() -> None:
    repo_id = os.environ.get("CHAT_MODEL", "")
    target_dir = os.environ.get("CHAT_MODEL_PATH", "/opt/models/chat")

    # Token from env or mounted secret
    token = os.environ.get("HF_TOKEN") or None
    if not token:
        secret_path = "/run/secrets/hf_token"
        if os.path.isfile(secret_path):
            with open(secret_path) as f:
                token = f.read().strip() or None

    if not repo_id:
        print("[build] No CHAT_MODEL specified - skipping chat model download")
        return

    try:
        download_chat_model(repo_id, target_dir, token)
    except Exception as e:
        print(f"[build] ERROR: Failed to download chat model: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

