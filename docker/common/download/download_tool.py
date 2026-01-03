#!/usr/bin/env python3
"""Download tool classifier model from HuggingFace at Docker build time.

This shared module is used by both TRT and vLLM Docker builds to download the
tool classifier model. The tool model is a PyTorch model that runs on both
engines without engine-specific compilation.
"""

import os
import sys

# Add parent to path for utils import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import get_hf_token, download_snapshot, log_success, log_skip


def main() -> None:
    repo_id = os.environ.get("TOOL_MODEL", "")
    target_dir = os.environ.get("TOOL_MODEL_PATH", "/opt/models/tool")
    
    if not repo_id:
        log_skip("No TOOL_MODEL specified - skipping tool model download")
        return
    
    token = get_hf_token()
    
    try:
        download_snapshot(repo_id, target_dir, token=token)
        log_success("Tool model downloaded and baked into image")
    except Exception as e:
        print(f"[build] ERROR: Failed to download tool model: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
