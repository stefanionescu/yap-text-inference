#!/usr/bin/env python3
"""Download model files (tokenizer, config, etc.) from HuggingFace at Docker build time.

For TRT engines, the model files (tokenizer, config) are typically stored in the 
same repo as the engine. This script downloads everything EXCEPT:
- .gitattributes
- README.md / README files
- trt-llm/ directory (engines are downloaded separately)
"""

import os
import sys


# Files and directories to exclude when downloading model files
IGNORE_PATTERNS = [
    ".gitattributes",
    "README.md",
    "README",
    "README.txt",
    "trt-llm/*",
    "trt-llm/**",
]


def download_model_files(
    repo_id: str,
    target_dir: str,
    token: str | None = None,
    ignore_patterns: list[str] | None = None,
) -> None:
    """Download model files from HuggingFace, excluding engine and metadata files.
    
    This downloads tokenizer, config, and other model files needed for inference,
    but excludes the TRT engine files (downloaded separately) and repo metadata.
    
    Args:
        repo_id: HuggingFace repo ID
        target_dir: Local directory to store model files
        token: Optional HuggingFace token for private repos
        ignore_patterns: Patterns to ignore (default: IGNORE_PATTERNS)
    """
    from huggingface_hub import snapshot_download

    if ignore_patterns is None:
        ignore_patterns = IGNORE_PATTERNS

    print(f"[build] Downloading model files from {repo_id}...")
    print(f"[build]   Target: {target_dir}")
    print(f"[build]   Ignoring: {ignore_patterns}")

    os.makedirs(target_dir, exist_ok=True)

    snapshot_download(
        repo_id=repo_id,
        local_dir=target_dir,
        ignore_patterns=ignore_patterns,
        token=token,
    )

    # Verify we got some model files
    files = os.listdir(target_dir)
    config_files = [f for f in files if "config" in f.lower() or "tokenizer" in f.lower()]
    
    print(f"[build] ✓ Downloaded {len(files)} file(s)")
    if config_files:
        print(f"[build]   Found config/tokenizer files: {config_files[:5]}")


def main() -> None:
    # For TRT builds, the model files come from the engine repo
    # This includes tokenizer, config, etc.
    repo_id = os.environ.get("TRT_ENGINE_REPO", "")
    target_dir = os.environ.get("CHAT_MODEL_PATH", "/opt/models/chat")

    # Token from env or mounted secret
    token = os.environ.get("HF_TOKEN") or None
    if not token:
        secret_path = "/run/secrets/hf_token"
        if os.path.isfile(secret_path):
            with open(secret_path) as f:
                token = f.read().strip() or None

    if not repo_id:
        print("[build] No TRT_ENGINE_REPO set - skipping model files download")
        return

    try:
        download_model_files(repo_id, target_dir, token)
        print("[build] ✓ Model files (tokenizer, config) baked into image")
    except Exception as e:
        print(f"[build] ERROR: Failed to download model files: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

