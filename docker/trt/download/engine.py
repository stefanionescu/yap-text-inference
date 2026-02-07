#!/usr/bin/env python3
"""Download pre-built TRT engine from HuggingFace at Docker build time."""

import os
import sys
import shutil

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

from utils import log_skip, log_success, get_hf_token, download_snapshot, verify_files_exist


def main() -> None:
    repo_id = os.environ.get("TRT_ENGINE_REPO", "")
    engine_label = os.environ.get("TRT_ENGINE_LABEL", "")
    target_dir = os.environ.get("TRT_ENGINE_DIR", "/opt/engines/trt-chat")
    
    if not repo_id or not engine_label:
        log_skip("No TRT_ENGINE_REPO/TRT_ENGINE_LABEL set - skipping engine download")
        return
    
    token = get_hf_token()
    
    print(f"[build] Downloading TRT engine from {repo_id}...")
    print(f"[build]   Engine label: {engine_label}")
    print(f"[build]   Target: {target_dir}")
    
    try:
        # Download engine files from nested structure
        download_snapshot(
            repo_id,
            target_dir,
            token=token,
            allow_patterns=[f"trt-llm/engines/{engine_label}/**"],
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
        engine_files = verify_files_exist(target_dir, file_extension=".engine")
        print(f"[build] ✓ Downloaded {len(engine_files)} engine file(s)")
        log_success("TRT engine baked into image")
        
    except Exception as e:
        print(f"[build] ERROR: Failed to download engine: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
