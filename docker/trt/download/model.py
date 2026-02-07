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

# Add common download utils to path (works in both dev and Docker contexts)
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

# Files and directories to exclude when downloading model files
IGNORE_PATTERNS = [
    ".gitattributes",
    "README.md",
    "README",
    "README.txt",
    "trt-llm/*",
    "trt-llm/**",
]


def main() -> None:
    # For TRT builds, the model files come from the engine repo
    # This includes tokenizer, config, etc.
    repo_id = os.environ.get("TRT_ENGINE_REPO", "")
    target_dir = os.environ.get("CHAT_MODEL_PATH", "/opt/models/chat")
    
    if not repo_id:
        log_skip("No TRT_ENGINE_REPO set - skipping model files download")
        return
    
    token = get_hf_token()
    
    try:
        download_snapshot(
            repo_id,
            target_dir,
            token=token,
            ignore_patterns=IGNORE_PATTERNS,
        )
        
        # Verify we got some model files
        files = os.listdir(target_dir)
        config_files = [f for f in files if "config" in f.lower() or "tokenizer" in f.lower()]
        
        print(f"[build] ✓ Downloaded {len(files)} file(s)")
        if config_files:
            print(f"[build]   Found config/tokenizer files: {config_files[:5]}")
        
        log_success("Model files (tokenizer, config) baked into image")
        
    except Exception as e:
        print(f"[build] ERROR: Failed to download model files: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
