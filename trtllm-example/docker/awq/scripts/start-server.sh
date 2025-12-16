#!/usr/bin/env bash
set -euo pipefail

# AWQ Docker image server startup script
# Pulls quantized checkpoint or engines from HF (no TRT repo clone), builds engine if needed, then starts server

echo "Starting Orpheus TTS Server (AWQ)"

# Source environment if available
if [[ -f /usr/local/bin/environment.sh ]]; then
  # shellcheck disable=SC1091
  source /usr/local/bin/environment.sh
fi

# Validate HF_DEPLOY_REPO_ID contains both "trt" and "awq" (case insensitive)
# AWQ Docker image only supports pre-quantized TRT-LLM AWQ engines
if [[ -n ${HF_DEPLOY_REPO_ID:-} ]]; then
  _repo_lower="${HF_DEPLOY_REPO_ID,,}"  # lowercase
  if [[ ! $_repo_lower =~ trt ]] || [[ ! $_repo_lower =~ awq ]]; then
    echo "ERROR: AWQ Docker image requires a pre-quantized TRT-LLM AWQ engine repo." >&2
    echo "       HF_DEPLOY_REPO_ID must contain both 'trt' and 'awq' (case insensitive)." >&2
    echo "       Got: HF_DEPLOY_REPO_ID=${HF_DEPLOY_REPO_ID}" >&2
    echo "       Example: yapwithai/orpheus-3b-tts-trt-awq" >&2
    exit 1
  fi
fi

# Always log to file and stream to Docker stdout
LOG_DIR=/app/logs
LOG_FILE=${LOG_DIR}/server.log
mkdir -p /app/.run "${LOG_DIR}" || true
touch "${LOG_FILE}" || true

# Helper: detect SM arch (e.g., sm80)
_detect_sm() {
  if [[ -n ${GPU_SM_ARCH:-} ]]; then
    echo "$GPU_SM_ARCH"
    return
  fi
  if command -v nvidia-smi >/dev/null 2>&1; then
    local cap
    cap=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -n1)
    if [[ -n $cap ]]; then
      echo "sm${cap/./}"
      return
    fi
  fi
  echo ""
}

# If HF_DEPLOY_REPO_ID is set, pull engines/checkpoints and optionally build
if [[ -n ${HF_DEPLOY_REPO_ID:-} ]]; then
  echo "HF remote deploy: ${HF_DEPLOY_REPO_ID}"
  export HF_HUB_ENABLE_HF_TRANSFER=1
  py_out=$(
    python - <<'PY'
import os
from pathlib import Path
from huggingface_hub import snapshot_download

repo_id=os.environ.get('HF_DEPLOY_REPO_ID')
use=os.environ.get('HF_DEPLOY_USE','auto').strip().lower()
engine_label=os.environ.get('HF_DEPLOY_ENGINE_LABEL','').strip()
workdir=os.environ.get('HF_DEPLOY_WORKDIR','') or '/opt/models/_hf_download'
gpu_sm=os.environ.get('GPU_SM_ARCH','').strip()
_token=os.environ.get('HUGGINGFACE_HUB_TOKEN') or os.environ.get('HF_TOKEN') or None

base=None

def dl(patterns):
    return snapshot_download(
        repo_id=repo_id,
        local_dir=workdir,
        local_dir_use_symlinks=False,
        allow_patterns=patterns,
        token=_token,
    )


def find_engine_dir(root: Path) -> tuple[str, str]:
    engines_dir = root / 'trt-llm' / 'engines'
    if not engines_dir.is_dir():
        return '', ''
    labels = [p.name for p in engines_dir.iterdir() if p.is_dir()]
    selected=''
    if engine_label and engine_label in labels:
        selected=engine_label
    elif len(labels)==1:
        selected=labels[0]
    elif gpu_sm:
        matches=[lab for lab in sorted(labels) if lab.startswith(gpu_sm)]
        if len(matches)==1:
            selected=matches[0]
    if selected:
        eng_dir = str(engines_dir/selected)
        return selected, eng_dir
    return '', ''

# Try engines first if allowed
if use in ('engines','auto'):
    try:
        patterns=[f"trt-llm/engines/{engine_label}/**"] if engine_label else ["trt-llm/engines/**", "trt-llm/engines/**/build_metadata.json"]
        base=Path(dl(patterns))
        sel, eng_dir = find_engine_dir(base)
        if sel:
            print("MODE=engines")
            print(f"ENGINE_LABEL={sel}")
            print(f"ENGINE_DIR={eng_dir}")
            raise SystemExit(0)
    except Exception as exc:
        print(f"MODE=error MSG={type(exc).__name__}:{exc}")
        raise SystemExit(0)

# If engines not found, try checkpoints if allowed
if use in ('checkpoints','auto'):
    try:
        base=Path(dl(["trt-llm/checkpoints/**"]))
        ckpt_dir = base / 'trt-llm' / 'checkpoints'
        if ckpt_dir.is_dir() and (ckpt_dir/ 'config.json').is_file():
            shards = list(ckpt_dir.glob('rank*.safetensors'))
            if shards:
                print("MODE=checkpoints")
                print(f"CHECKPOINT_DIR={ckpt_dir}")
                raise SystemExit(0)
    except Exception as exc:
        print(f"MODE=error MSG={type(exc).__name__}:{exc}")
        raise SystemExit(0)

print("MODE=none")
PY
  )
  mode=$(echo "$py_out" | awk -F= '/^MODE=/{print $2; exit}')
  if [[ $mode == "engines" ]]; then
    TRTLLM_ENGINE_DIR=$(echo "$py_out" | awk -F= '/^ENGINE_DIR=/{print $2; exit}')
    if [[ -f "$TRTLLM_ENGINE_DIR/rank0.engine" && -f "$TRTLLM_ENGINE_DIR/config.json" ]]; then
      export TRTLLM_ENGINE_DIR
      echo "Using prebuilt engine: $TRTLLM_ENGINE_DIR"
    else
      echo "ERROR: downloaded engines missing required files" >&2
    fi
  elif [[ $mode == "checkpoints" ]]; then
    CHECKPOINT_DIR=$(echo "$py_out" | awk -F= '/^CHECKPOINT_DIR=/{print $2; exit}')
    if [[ -f "$CHECKPOINT_DIR/config.json" ]] && ls "$CHECKPOINT_DIR"/rank*.safetensors >/dev/null 2>&1; then
      echo "Building engine from checkpoint: $CHECKPOINT_DIR"
      : "${TRTLLM_ENGINE_DIR:=${ENGINES_DIR}/orpheus-trt-awq}"
      trtllm-build \
        --checkpoint_dir "$CHECKPOINT_DIR" \
        --output_dir "$TRTLLM_ENGINE_DIR" \
        --gemm_plugin auto \
        --gpt_attention_plugin float16 \
        --context_fmha enable \
        --paged_kv_cache enable \
        --remove_input_padding enable \
        --max_input_len "${TRTLLM_MAX_INPUT_LEN:-48}" \
        --max_seq_len "$((${TRTLLM_MAX_INPUT_LEN:-48} + ${TRTLLM_MAX_OUTPUT_LEN:-1162}))" \
        --max_batch_size "${TRTLLM_MAX_BATCH_SIZE:-16}" \
        --log_level info \
        --workers "$(nproc --all)"
    else
      echo "ERROR: downloaded checkpoint invalid (missing config or shards)" >&2
    fi
  else
    err=$(echo "$py_out" | sed -n 's/.*MSG=//p')
    if [[ -n $err ]]; then
      echo "HF query error: $err" >&2
    fi
    echo "No usable artifacts found in HF repo; expecting a mounted engine."
  fi
fi

# Final validation of engine dir
if [[ -z ${TRTLLM_ENGINE_DIR:-} || ! -f "${TRTLLM_ENGINE_DIR}/rank0.engine" ]]; then
  echo "ERROR: TensorRT-LLM engine not available at TRTLLM_ENGINE_DIR=$TRTLLM_ENGINE_DIR" >&2
  echo "       Provide HF_DEPLOY_REPO_ID with engines/checkpoints, or mount an engine directory." >&2
  exit 1
fi

# Optional: Download model if MODEL_ID is provided and model doesn't exist
if [[ -n ${MODEL_ID:-} && -n ${HF_TOKEN:-} ]]; then
  MODEL_NAME=$(basename "$MODEL_ID")
  MODEL_PATH="${MODELS_DIR}/${MODEL_NAME}-hf"

  if [[ ! -d $MODEL_PATH ]]; then
    echo "Downloading model $MODEL_ID to $MODEL_PATH..."
    python -c "
import os
from huggingface_hub import snapshot_download

model_id = os.environ['MODEL_ID']
token = os.environ['HF_TOKEN']
local_dir = '$MODEL_PATH'

os.makedirs(local_dir, exist_ok=True)
snapshot_download(
    repo_id=model_id, 
    local_dir=local_dir,
    local_dir_use_symlinks=False, 
    token=token
)
print(f'Downloaded {model_id} to {local_dir}')
"
  else
    echo "Model already exists at $MODEL_PATH"
  fi
fi

echo "Configuration:"
echo "   Engine Directory: $TRTLLM_ENGINE_DIR"
echo "   Models Directory: ${MODELS_DIR}"
echo "   Host: ${HOST:-0.0.0.0}"
echo "   Port: ${PORT:-8000}"

# Start the FastAPI server
echo "Starting server..."
# Run server in background, append logs to file
uvicorn server.server:app \
  --host "${HOST:-0.0.0.0}" \
  --port "${PORT:-8000}" \
  --timeout-keep-alive 75 \
  --log-level info >>"${LOG_FILE}" 2>&1 &
SERVER_PID=$!

# Run post-start tests via dedicated script (prints to console); ignore errors
if [[ -x /usr/local/bin/warmup.sh ]]; then
  /usr/local/bin/warmup.sh || true
fi

echo "[start-server] Server PID: ${SERVER_PID}"
echo "[start-server] Tailing ${LOG_FILE} (Ctrl-C to detach; server keeps running)"
# Foreground tail so container stays up and logs stream to Docker
exec tail -n +1 -F "${LOG_FILE}"
