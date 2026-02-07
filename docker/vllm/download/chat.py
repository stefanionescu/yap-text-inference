#!/usr/bin/env python3
"""Download pre-quantized chat model from HuggingFace at Docker build time."""

import os
import sys

# Add common download utils to path (works in both dev and Docker contexts)
# In Docker: /app/download/ -> /app/common/download/
# In dev: docker/vllm/download/ -> docker/common/download/
script_dir = os.path.dirname(os.path.abspath(__file__))
common_paths = [
    os.path.join(script_dir, "..", "common", "download"),  # Docker: /app/common/download
    os.path.join(script_dir, "..", "..", "common", "download"),  # Dev: docker/common/download
]
for path in common_paths:
    if os.path.isdir(path):
        sys.path.insert(0, path)
        break

from utils import log_skip, log_success, get_hf_token, download_snapshot


def main() -> None:
    repo_id = os.environ.get("CHAT_MODEL", "")
    target_dir = os.environ.get("CHAT_MODEL_PATH", "/opt/models/chat")
    
    if not repo_id:
        log_skip("No CHAT_MODEL specified - skipping chat model download")
        return
    
    token = get_hf_token()
    
    try:
        download_snapshot(repo_id, target_dir, token=token)
        log_success("Chat model downloaded and baked into image")
    except Exception as e:
        print(f"[build] ERROR: Failed to download chat model: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
