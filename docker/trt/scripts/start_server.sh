#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

cd /app
ROOT_DIR="${ROOT_DIR:-/app}"

# ============================================================================
# Download TRT engines/checkpoints from HuggingFace if not already present
# If a checkpoint is found, build an engine inside the container.
# ============================================================================
if [ "${DEPLOY_CHAT}" = "1" ]; then
  if [ -n "${TRT_ENGINE_REPO:-}" ]; then
    # Detect GPU SM architecture for variant selection
    GPU_SM=""
    if command -v nvidia-smi >/dev/null 2>&1; then
      cap=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -n1 || true)
      if [ -n "${cap}" ]; then
        # shellcheck disable=SC2034  # Used by Python resolver
        GPU_SM="sm${cap/./}"
      fi
    fi

    log_info "[trt] Resolving artifacts from ${TRT_ENGINE_REPO}..."
py_out=$(
      PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" python - <<'PYPULL'
import os
import sys
from pathlib import Path

show_hf_logs = os.environ.get("SHOW_HF_LOGS", "0").lower() in ("1", "true", "yes")
if show_hf_logs:
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"
    os.environ.pop("TQDM_DISABLE", None)
    try:
        from huggingface_hub.utils import enable_progress_bars
        enable_progress_bars()
    except Exception:
        pass
else:
    from src.scripts.filters import configure
    configure()

from huggingface_hub import snapshot_download, list_repo_tree

repo_id=os.environ.get('TRT_ENGINE_REPO','').strip()
engine_dir=os.environ.get('TRT_ENGINE_DIR','/opt/engines/trt-chat')
gpu_sm=os.environ.get('GPU_SM','').strip()
token=os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_HUB_TOKEN') or None
engine_label=os.environ.get('TRT_ENGINE_LABEL','').strip()

if not repo_id:
    print("MODE=none")
    raise SystemExit(0)

files=list(list_repo_tree(repo_id, token=token))
paths=[f.path for f in files]

# Collect available engine labels
engine_labels=set()
for p in paths:
    if p.startswith("trt-llm/engines/"):
        parts=p.split("/")
        if len(parts)>=4:
            engine_labels.add(parts[3])

selected=""
if engine_labels:
    if engine_label and engine_label in engine_labels:
        selected=engine_label
    elif len(engine_labels)==1:
        selected=next(iter(engine_labels))
    elif gpu_sm:
        matches=[lab for lab in sorted(engine_labels) if lab.startswith(gpu_sm)]
        if len(matches)==1:
            selected=matches[0]

if selected:
    local=snapshot_download(
        repo_id=repo_id,
        local_dir=engine_dir,
        allow_patterns=[f"trt-llm/engines/{selected}/**", "trt-llm/engines/**/build_metadata.json"],
        token=token,
    )
    eng_dir=str(Path(local)/"trt-llm"/"engines"/selected)
    print("MODE=engines")
    print(f"ENGINE_DIR={eng_dir}")
    print(f"ENGINE_LABEL={selected}")
    raise SystemExit(0)

# Fallback to checkpoints
if any(p.startswith("trt-llm/checkpoints/") for p in paths):
    local=snapshot_download(
        repo_id=repo_id,
        local_dir=engine_dir,
        allow_patterns=["trt-llm/checkpoints/**"],
        token=token,
    )
    ckpt_dir=str(Path(local)/"trt-llm"/"checkpoints")
    if (Path(ckpt_dir)/"config.json").is_file():
        print("MODE=checkpoints")
    print(f"CHECKPOINT_DIR={ckpt_dir}")
    raise SystemExit(0)

print("MODE=none")
PYPULL
    )

    mode=$(echo "$py_out" | awk -F= '/^MODE=/{print $2; exit}')
    if [ "$mode" = "engines" ]; then
      TRT_ENGINE_DIR=$(echo "$py_out" | awk -F= '/^ENGINE_DIR=/{print $2; exit}')
      if [ -f "${TRT_ENGINE_DIR}/rank0.engine" ]; then
        log_info "[trt] Using downloaded engine: ${TRT_ENGINE_DIR}"
      else
        log_error "[trt] ✗ Downloaded engine missing rank0.engine"
        exit 1
      fi
    elif [ "$mode" = "checkpoints" ]; then
      CHECKPOINT_DIR=$(echo "$py_out" | awk -F= '/^CHECKPOINT_DIR=/{print $2; exit}')
      if [ -z "${CHECKPOINT_DIR}" ] || [ ! -f "${CHECKPOINT_DIR}/config.json" ]; then
        log_error "[trt] ✗ Downloaded checkpoint invalid (missing config.json)"
        exit 1
      fi
      # Build engine from checkpoint
      : "${TRT_ENGINE_DIR:=/opt/engines/trt-chat}"
      MAX_IN="${TRT_MAX_INPUT_LEN:-${TRTLLM_MAX_INPUT_LEN:-60}}"
      MAX_OUT="${TRT_MAX_OUTPUT_LEN:-${TRTLLM_MAX_OUTPUT_LEN:-4096}}"
      MAX_BATCH="${TRT_MAX_BATCH_SIZE:-${TRTLLM_MAX_BATCH_SIZE:-16}}"
      log_info "[trt] Building engine from checkpoint: ${CHECKPOINT_DIR}"
      trtllm-build \
        --checkpoint_dir "${CHECKPOINT_DIR}" \
        --output_dir "${TRT_ENGINE_DIR}" \
        --gemm_plugin auto \
        --gpt_attention_plugin float16 \
        --context_fmha enable \
        --use_paged_context_fmha enable \
        --kv_cache_type paged \
        --remove_input_padding enable \
        --max_input_len "${MAX_IN}" \
        --max_seq_len "$((MAX_IN + MAX_OUT))" \
        --max_batch_size "${MAX_BATCH}" \
        --log_level info \
        --workers "$(nproc --all)" || {
          log_error "[trt] ✗ trtllm-build failed from checkpoint"
          exit 1
        }
    else
      log_warn "[trt] ⚠ No engines or checkpoints found in repo; expecting mounted engine"
    fi
  else
    log_warn "[trt] ⚠ TRT_ENGINE_REPO not set - expecting engine to be mounted at ${TRT_ENGINE_DIR}"
  fi

  # Final validation
  if [ ! -f "${TRT_ENGINE_DIR}/rank0.engine" ]; then
    log_error "[trt] ✗ TRT engine not found at ${TRT_ENGINE_DIR}/rank0.engine"
    log_error "[trt] ✗ Either set TRT_ENGINE_REPO or mount an engine directory"
    exit 1
  fi

  log_success "[trt] ✓ TRT engine validated at ${TRT_ENGINE_DIR}"
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
  log_error "[trt] ✗ uvicorn not found in container. Ensure dependencies are installed."
  exit 127
fi

log_info "[trt] Starting server..."
"${UVICORN_CMD[@]}" &
SERVER_PID=$!

# Run warmup in background
"${SCRIPT_DIR}/warmup.sh" &

# Wait on server (container stays alive)
wait "${SERVER_PID}"
