#!/usr/bin/env bash
set -euo pipefail

# Prepare TensorRT-LLM checkpoint (INT4-AWQ or base FP16/FP8) and build engine.

# Defaults (override via env or flags)
MODEL_PRESET=${MODEL_PRESET:-canopy}
MODEL_ID=${MODEL_ID:-}
if [[ -z ${MODEL_ID} ]]; then
  if [[ ${MODEL_PRESET} == "fast" ]]; then
    MODEL_ID="yapwithai/fast-orpheus-3b-0.1-ft"
  else
    MODEL_ID="yapwithai/canopy-orpheus-3b-0.1-ft"
  fi
fi
TRTLLM_REPO_DIR=${TRTLLM_REPO_DIR:-/opt/TensorRT-LLM}
MODELS_DIR=${MODELS_DIR:-/opt/models}
CHECKPOINT_DIR=${CHECKPOINT_DIR:-/opt/checkpoints/orpheus-trtllm-ckpt-int4-awq}
ENGINE_OUTPUT_DIR=${TRTLLM_ENGINE_DIR:-/opt/engines/orpheus-trt-awq}

# Build parameters (match project defaults)
TRTLLM_DTYPE=${TRTLLM_DTYPE:-float16}
TRTLLM_MAX_INPUT_LEN=${TRTLLM_MAX_INPUT_LEN:-48}
TRTLLM_MAX_OUTPUT_LEN=${TRTLLM_MAX_OUTPUT_LEN:-1162}
TRTLLM_MAX_BATCH_SIZE=${TRTLLM_MAX_BATCH_SIZE:-16}
AWQ_BLOCK_SIZE=${AWQ_BLOCK_SIZE:-128}
CALIB_SIZE=${CALIB_SIZE:-256}
PRECISION_MODE=${ORPHEUS_PRECISION_MODE:-quantized}
BASE_INFERENCE_DTYPE=${BASE_INFERENCE_DTYPE:-}
TRTLLM_CONVERT_SCRIPT=${TRTLLM_CONVERT_SCRIPT:-}
PYTHON_EXEC=${PYTHON_EXEC:-python}

_detect_gpu_sm() {
  if command -v nvidia-smi >/dev/null 2>&1; then
    local cap
    cap=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -n1 | tr -d '\r')
    if [[ -n $cap ]]; then
      local major=${cap%%.*}
      local minor=${cap##*.}
      printf "sm%s%s" "$major" "$minor"
      return 0
    fi
  fi
  echo ""
}

_gpu_supports_fp8() {
  local sm="$1"
  [[ -z $sm ]] && return 1
  local digits="${sm#sm}"
  [[ -z $digits ]] && return 1
  local num=$((10#$digits))
  if ((num >= 90)); then
    return 0
  fi
  if ((num == 89)); then
    return 0
  fi
  return 1
}

_resolve_base_dtype() {
  local sm
  sm=$(_detect_gpu_sm)
  if _gpu_supports_fp8 "$sm"; then
    echo "fp8_e4m3"
  else
    echo "float16"
  fi
}

usage() {
  echo "Usage: $0 [--model ID_OR_PATH] [--checkpoint-dir DIR] [--engine-dir DIR] [--dtype float16|fp8_e4m3|bfloat16]"
  echo "          [--max-input-len N] [--max-output-len N] [--max-batch-size N] [--awq-block-size N]"
  echo "          [--calib-size N] [--precision-mode quantized|base] [--no-quantize] [--force]"
}

ARGS=()
FORCE_REBUILD=false
CLI_DTYPE_OVERRIDE=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL_ID="$2"
      shift 2
      ;;
    --checkpoint-dir)
      CHECKPOINT_DIR="$2"
      shift 2
      ;;
    --engine-dir)
      ENGINE_OUTPUT_DIR="$2"
      shift 2
      ;;
    --dtype)
      TRTLLM_DTYPE="$2"
      CLI_DTYPE_OVERRIDE=true
      shift 2
      ;;
    --max-input-len)
      TRTLLM_MAX_INPUT_LEN="$2"
      shift 2
      ;;
    --max-output-len)
      TRTLLM_MAX_OUTPUT_LEN="$2"
      shift 2
      ;;
    --max-batch-size)
      TRTLLM_MAX_BATCH_SIZE="$2"
      shift 2
      ;;
    --awq-block-size)
      AWQ_BLOCK_SIZE="$2"
      shift 2
      ;;
    --calib-size)
      CALIB_SIZE="$2"
      shift 2
      ;;
    --precision-mode)
      PRECISION_MODE="$2"
      shift 2
      ;;
    --no-quantize)
      PRECISION_MODE="base"
      shift
      ;;
    --force)
      FORCE_REBUILD=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done
set -- "${ARGS[@]:-}"

case "$PRECISION_MODE" in
  quantized | base) ;;
  *)
    echo "ERROR: --precision-mode must be 'quantized' or 'base' (got '${PRECISION_MODE}')" >&2
    exit 1
    ;;
esac

if [[ $PRECISION_MODE == "base" ]]; then
  if [[ -n $BASE_INFERENCE_DTYPE ]]; then
    TRTLLM_DTYPE="$BASE_INFERENCE_DTYPE"
    echo "[build] Base precision override via BASE_INFERENCE_DTYPE=${TRTLLM_DTYPE}"
  elif [[ ${ORPHEUS_TRTLLM_DTYPE_DEFAULTED:-0} == "1" && $CLI_DTYPE_OVERRIDE != true ]]; then
    TRTLLM_DTYPE="$(_resolve_base_dtype)"
    echo "[build] Auto-selected base inference dtype: ${TRTLLM_DTYPE}"
  else
    echo "[build] Base precision using existing TRTLLM_DTYPE=${TRTLLM_DTYPE}"
  fi
  gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 || true)
  [[ -n $gpu_name ]] && echo "[build] Detected GPU: ${gpu_name}"
fi

echo "=== Prepare checkpoint (${PRECISION_MODE}) and build TRT-LLM engine ==="

# Env validation
if [[ -z ${HF_TOKEN:-} ]]; then
  echo "ERROR: HF_TOKEN not set" >&2
  exit 1
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "ERROR: nvidia-smi not detected. GPU required for engine build." >&2
  exit 1
fi

if [[ ! -d $TRTLLM_REPO_DIR ]]; then
  echo "ERROR: TRTLLM_REPO_DIR not found at $TRTLLM_REPO_DIR" >&2
  exit 1
fi

if [[ $PRECISION_MODE == "quantized" ]]; then
  quant_requirements="$TRTLLM_REPO_DIR/examples/quantization/requirements.txt"
  if [[ -f $quant_requirements ]]; then
    echo "[build] Installing quantization requirements..."
    pip install -r "$quant_requirements"
    # Upgrade urllib3 to fix GHSA-gm62-xv2j-4w53 and GHSA-2xpw-w6gg-jr37
    pip install 'urllib3>=2.6.0'
  else
    echo "[build] WARNING: quantization requirements.txt not found, continuing"
  fi
fi

export HF_HUB_ENABLE_HF_TRANSFER=1
export HUGGING_FACE_HUB_TOKEN="${HUGGING_FACE_HUB_TOKEN:-$HF_TOKEN}"
export HF_HUB_TOKEN="${HF_HUB_TOKEN:-$HF_TOKEN}"

# Resolve model directory (use pre-downloaded model inside image)
local_model_dir="$MODEL_ID"
if [[ ! -d $MODEL_ID ]]; then
  basename="${MODEL_ID##*/}"
  local_model_dir="${MODELS_DIR}/${basename}-hf"
  if [[ ! -d $local_model_dir ]]; then
    echo "ERROR: Expected pre-downloaded model at ${local_model_dir}. Rebuild image with HF_TOKEN secret."
    exit 1
  else
    echo "[build] Using cached HF model at ${local_model_dir}"
  fi
else
  echo "[build] Using local model directory: ${MODEL_ID}"
fi

# Skip if already built
if [[ -f "$ENGINE_OUTPUT_DIR/rank0.engine" && -f "$ENGINE_OUTPUT_DIR/config.json" && $FORCE_REBUILD != true ]]; then
  echo "[build] Engine already exists at: $ENGINE_OUTPUT_DIR"
  echo "[build] Use --force to rebuild"
  exit 0
fi

echo "[build] Configuration:"
echo "  Model: ${MODEL_ID}"
echo "  Precision mode: ${PRECISION_MODE}"
echo "  Checkpoint dir: ${CHECKPOINT_DIR}"
echo "  Engine dir: ${ENGINE_OUTPUT_DIR}"
echo "  DType: ${TRTLLM_DTYPE}"
echo "  Max input/output: ${TRTLLM_MAX_INPUT_LEN}/${TRTLLM_MAX_OUTPUT_LEN}"
echo "  Max batch size: ${TRTLLM_MAX_BATCH_SIZE}"
echo "  AWQ block size: ${AWQ_BLOCK_SIZE}  Calib size: ${CALIB_SIZE}"

rm -rf "$CHECKPOINT_DIR"
mkdir -p "$CHECKPOINT_DIR"

if [[ $PRECISION_MODE == "base" ]]; then
  echo "[build] Step 1/2: Converting HF weights to base TensorRT-LLM checkpoint (${TRTLLM_DTYPE})"
  convert_script="${TRTLLM_CONVERT_SCRIPT}"
  if [[ -n $convert_script && ! -f $convert_script ]]; then
    echo "ERROR: TRTLLM_CONVERT_SCRIPT='${convert_script}' not found" >&2
    exit 1
  fi
  if [[ -z $convert_script ]]; then
    convert_script=$(find "$TRTLLM_REPO_DIR" -name convert_checkpoint.py -print 2>/dev/null | head -n1 || true)
  fi
  if [[ -z $convert_script ]]; then
    echo "ERROR: convert_checkpoint.py not found in ${TRTLLM_REPO_DIR}; set TRTLLM_CONVERT_SCRIPT" >&2
    exit 1
  fi
  "$PYTHON_EXEC" "$convert_script" \
    --model_dir "$local_model_dir" \
    --output_dir "$CHECKPOINT_DIR" \
    --dtype "$TRTLLM_DTYPE" \
    --tp_shards 1 \
    --pp_shards 1
else
  echo "[build] Step 1/2: Quantize to INT4-AWQ"
  quant_script="$TRTLLM_REPO_DIR/examples/quantization/quantize.py"
  if [[ ! -f $quant_script ]]; then
    echo "ERROR: quantize.py not found at $quant_script" >&2
    exit 1
  fi
  "$PYTHON_EXEC" "$quant_script" \
    --model_dir "$local_model_dir" \
    --output_dir "$CHECKPOINT_DIR" \
    --dtype "$TRTLLM_DTYPE" \
    --qformat int4_awq \
    --awq_block_size "$AWQ_BLOCK_SIZE" \
    --calib_size "$CALIB_SIZE" \
    --kv_cache_dtype int8 \
    --batch_size 16
fi

echo "[build] Step 2/2: Build TensorRT-LLM engine"
mkdir -p "$ENGINE_OUTPUT_DIR"

trtllm-build \
  --checkpoint_dir "$CHECKPOINT_DIR" \
  --output_dir "$ENGINE_OUTPUT_DIR" \
  --gemm_plugin auto \
  --gpt_attention_plugin float16 \
  --context_fmha enable \
  --paged_kv_cache enable \
  --remove_input_padding enable \
  --max_input_len "$TRTLLM_MAX_INPUT_LEN" \
  --max_seq_len "$((TRTLLM_MAX_INPUT_LEN + TRTLLM_MAX_OUTPUT_LEN))" \
  --max_batch_size "$TRTLLM_MAX_BATCH_SIZE" \
  --log_level info \
  --workers "$(nproc --all)"

# Copy generation_config.json from HF model
if [[ -f "${local_model_dir}/generation_config.json" ]]; then
  cp "${local_model_dir}/generation_config.json" "${ENGINE_OUTPUT_DIR}/"
  echo "[build] Copied generation_config.json to engine directory"
fi

echo "[build] ✓ Done. Engine at: $ENGINE_OUTPUT_DIR"
