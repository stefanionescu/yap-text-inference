#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

if [ "${DEPLOY_CHAT:-0}" = "1" ]; then
  log_info "[trt] Starting TRT-LLM server on :8000"
else
  log_info "[trt] Starting server on :8000 (tool classifier only)"
fi
cd /app

# Log key environment variables
log_info "[trt] GPU=${DETECTED_GPU_NAME:-unknown}"
log_info "[trt] DEPLOY_MODE=${DEPLOY_MODE:-both}"
if [ "${DEPLOY_CHAT:-0}" = "1" ]; then
  log_info "[trt] CHAT_MODEL=${CHAT_MODEL:-none} (tokenizer)"
  log_info "[trt] TRT_ENGINE_REPO=${TRT_ENGINE_REPO:-none}"
  log_info "[trt] TRT_ENGINE_DIR=${TRT_ENGINE_DIR:-/opt/engines/trt-chat}"
  log_info "[trt] TRT_KV_FREE_GPU_FRAC=${TRT_KV_FREE_GPU_FRAC:-0.92}"
  log_info "[trt] TRT_KV_ENABLE_BLOCK_REUSE=${TRT_KV_ENABLE_BLOCK_REUSE:-1}"
fi
if [ "${DEPLOY_TOOL:-0}" = "1" ]; then
  log_info "[trt] TOOL_MODEL=${TOOL_MODEL:-none} (PyTorch classifier)"
fi

# ============================================================================
# Download TRT engines from HuggingFace if not already present
# ============================================================================
if [ "${DEPLOY_CHAT}" = "1" ]; then
  if [ -n "${TRT_ENGINE_REPO:-}" ]; then
    # Check if engine already exists
    if [ -f "${TRT_ENGINE_DIR}/rank0.engine" ] && [ -f "${TRT_ENGINE_DIR}/config.json" ]; then
      log_info "[trt] TRT engine already present at ${TRT_ENGINE_DIR}"
    else
      log_info "[trt] Downloading TRT engine from ${TRT_ENGINE_REPO}..."
      
      # Detect GPU SM architecture for engine selection
      GPU_SM=""
      if command -v nvidia-smi >/dev/null 2>&1; then
        cap=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -n1 || true)
        if [ -n "${cap}" ]; then
          GPU_SM="sm${cap/./}"
          log_info "[trt] Detected GPU SM architecture: ${GPU_SM}"
        fi
      fi
      
      # Download engine from HuggingFace
      python - <<PYPULL
import os
import sys
from pathlib import Path
from huggingface_hub import snapshot_download, hf_hub_download, list_repo_tree

repo_id = os.environ.get('TRT_ENGINE_REPO', '')
engine_dir = os.environ.get('TRT_ENGINE_DIR', '/opt/engines/trt-chat')
gpu_sm = os.environ.get('GPU_SM', '${GPU_SM}')
token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_HUB_TOKEN') or None

if not repo_id:
    print("[trt-download] TRT_ENGINE_REPO not set", file=sys.stderr)
    sys.exit(1)

os.makedirs(engine_dir, exist_ok=True)

try:
    # Try to find engines directory structure
    files = list(list_repo_tree(repo_id, token=token))
    file_paths = [f.path for f in files]
    
    # Look for engines in various patterns
    engine_patterns = []
    
    # Pattern 1: trt-llm/engines/<sm_arch>/
    for f in file_paths:
        if f.startswith('trt-llm/engines/'):
            parts = f.split('/')
            if len(parts) >= 3:
                engine_patterns.append(parts[2])
    
    # Pattern 2: engines/<sm_arch>/
    for f in file_paths:
        if f.startswith('engines/') and not f.startswith('engines/'):
            parts = f.split('/')
            if len(parts) >= 2:
                engine_patterns.append(parts[1])
    
    # Pattern 3: root level engine files
    has_root_engine = any('rank0.engine' in f for f in file_paths)
    
    selected_pattern = None
    download_patterns = None
    
    if engine_patterns:
        engine_patterns = list(set(engine_patterns))
        print(f"[trt-download] Found engine variants: {engine_patterns}")
        
        # Try to match GPU SM arch
        if gpu_sm:
            matches = [p for p in engine_patterns if p.startswith(gpu_sm)]
            if matches:
                selected_pattern = matches[0]
                print(f"[trt-download] Selected engine variant: {selected_pattern}")
        
        if not selected_pattern and len(engine_patterns) == 1:
            selected_pattern = engine_patterns[0]
            print(f"[trt-download] Using only available variant: {selected_pattern}")
        
        if selected_pattern:
            # Try trt-llm/engines/ first
            download_patterns = [f"trt-llm/engines/{selected_pattern}/**"]
            if not any(f.startswith(f'trt-llm/engines/{selected_pattern}') for f in file_paths):
                download_patterns = [f"engines/{selected_pattern}/**"]
    
    elif has_root_engine:
        # Engine files at root level
        download_patterns = ["*.engine", "*.json", "*.safetensors"]
        print("[trt-download] Downloading root-level engine files")
    
    if not download_patterns:
        # Fall back to downloading entire repo
        print("[trt-download] No specific engine pattern found, downloading entire repo")
        download_patterns = None
    
    # Download
    local_path = snapshot_download(
        repo_id=repo_id,
        local_dir=engine_dir,
        allow_patterns=download_patterns,
        token=token
    )
    
    # Find the actual engine directory
    engine_path = Path(local_path)
    
    # Check various possible locations
    possible_paths = [
        engine_path,
        engine_path / 'trt-llm' / 'engines' / (selected_pattern or ''),
        engine_path / 'engines' / (selected_pattern or ''),
    ]
    
    for p in possible_paths:
        if p.exists() and (p / 'rank0.engine').exists():
            if str(p) != engine_dir:
                # Move files to expected location
                import shutil
                for f in p.iterdir():
                    dest = Path(engine_dir) / f.name
                    if f.is_file():
                        shutil.copy2(f, dest)
                    elif f.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(f, dest)
            print(f"[trt-download] Engine ready at {engine_dir}")
            sys.exit(0)
    
    print(f"[trt-download] Could not find engine files after download", file=sys.stderr)
    print(f"[trt-download] Contents of {local_path}:", file=sys.stderr)
    for item in Path(local_path).rglob('*'):
        print(f"  {item}", file=sys.stderr)
    sys.exit(1)
    
except Exception as e:
    print(f"[trt-download] Failed to download TRT engine: {e}", file=sys.stderr)
    sys.exit(1)
PYPULL
      
      if [ $? -ne 0 ]; then
        log_error "[trt] Failed to download TRT engine. Exiting."
        exit 1
      fi
    fi
  else
    log_warn "[trt] TRT_ENGINE_REPO not set - expecting engine to be mounted at ${TRT_ENGINE_DIR}"
  fi
  
  # Final validation
  if [ ! -f "${TRT_ENGINE_DIR}/rank0.engine" ]; then
    log_error "[trt] TRT engine not found at ${TRT_ENGINE_DIR}/rank0.engine"
    log_error "[trt] Either set TRT_ENGINE_REPO or mount an engine directory"
    exit 1
  fi
  
  log_success "[trt] TRT engine validated at ${TRT_ENGINE_DIR}"
fi

# ============================================================================
# Start the server
# ============================================================================

# Resolve uvicorn command
if command -v uvicorn >/dev/null 2>&1; then
  UVICORN_CMD=(uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
elif command -v python >/dev/null 2>&1 && python -c "import uvicorn" 2>/dev/null; then
  UVICORN_CMD=(python -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
elif command -v python3 >/dev/null 2>&1 && python3 -c "import uvicorn" 2>/dev/null; then
  UVICORN_CMD=(python3 -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
else
  log_error "[trt] uvicorn not found in container. Ensure dependencies are installed."
  exit 127
fi

log_info "[trt] Starting uvicorn server..."
"${UVICORN_CMD[@]}" &
SERVER_PID=$!

# Run warmup in background
log_info "[trt] Running warmup validation in background..."
"${SCRIPT_DIR}/warmup.sh" &

# Wait on server (container stays alive)
wait "${SERVER_PID}"

