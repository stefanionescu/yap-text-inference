#!/usr/bin/env bash
set -euo pipefail

source "custom/lib/common.sh"
load_env_if_present
load_environment "$@"
source "custom/build/helpers.sh"

echo "[step:quant] Preparing checkpoint..."

VENV_DIR="${VENV_DIR:-$PWD/.venv}"
if [ -d "$VENV_DIR" ]; then
  # shellcheck disable=SC1090,SC1091
  source "$VENV_DIR/bin/activate"
fi

TRTLLM_REPO_DIR="${TRTLLM_REPO_DIR:-$PWD/.trtllm-repo}"
CHECKPOINT_DIR="${CHECKPOINT_DIR:-$PWD/models/orpheus-trtllm-ckpt-int4-awq}"
PYTHON_EXEC="${PYTHON_EXEC:-python}"
TRTLLM_DTYPE="${TRTLLM_DTYPE:-float16}"
AWQ_BLOCK_SIZE="${AWQ_BLOCK_SIZE:-128}"
CALIB_SIZE="${CALIB_SIZE:-256}"
PRECISION_MODE="${ORPHEUS_PRECISION_MODE:-quantized}"

if [[ ${SKIP_QUANTIZATION:-false} == true ]]; then
  echo "[step:quant] Skipping checkpoint prep (provided checkpoint)"
  _validate_downloaded_checkpoint "${CHECKPOINT_DIR}"
  exit 0
fi

export HF_HUB_ENABLE_HF_TRANSFER=1

_prepare_model_repo() {
  local model_path="${MODEL_ID}"
  if [[ -z ${model_path} ]]; then
    echo "[step:quant] ERROR: MODEL_ID unset" >&2
    return 1
  fi
  if [[ -d ${model_path} ]]; then
    echo "[step:quant] Using local model directory: ${model_path}" >&2
    echo "${model_path}"
    return 0
  fi
  local target
  target="${PWD}/models/$(basename "${model_path}")-hf"
  if [[ ! -d ${target} ]]; then
    echo "[step:quant] Downloading model from HuggingFace: ${model_path}" >&2
    mkdir -p "${target}"
    "${PYTHON_EXEC}" -c "
from huggingface_hub import snapshot_download
snapshot_download(repo_id='${model_path}', local_dir='${target}', local_dir_use_symlinks=False)
print('✓ Downloaded complete model repository')
" >&2
  else
    echo "[step:quant] Using cached HF model at ${target}" >&2
  fi
  echo "${target}"
}

if [[ -d ${CHECKPOINT_DIR} && ${FORCE_REBUILD:-false} != true ]]; then
  echo "[step:quant] Reusing existing checkpoint at ${CHECKPOINT_DIR}"
else
  rm -rf "${CHECKPOINT_DIR}"
  mkdir -p "${CHECKPOINT_DIR}"
  local_model_dir="$(_prepare_model_repo)"
  if [[ -z ${local_model_dir} ]]; then
    echo "[step:quant] ERROR: Failed to prepare local model directory" >&2
    exit 1
  fi

  if [[ ${PRECISION_MODE} == "base" ]]; then
    echo "[step:quant] Converting HF weights to base TensorRT-LLM checkpoint (${TRTLLM_DTYPE})..."

    convert_script="${TRTLLM_CONVERT_SCRIPT:-${TRTLLM_REPO_DIR}/examples/models/core/llama/convert_checkpoint.py}"
    if [[ ! -f $convert_script ]]; then
      echo "[step:quant] ERROR: LLaMA converter not found at '$convert_script'." >&2
      echo "[step:quant]        Ensure TensorRT-LLM repo is synced or set TRTLLM_CONVERT_SCRIPT explicitly." >&2
      exit 1
    fi

    if [[ $convert_script == *"/redrafter/"* ]]; then
      echo "[step:quant] ERROR: Detected redrafter convert script ($convert_script); set TRTLLM_CONVERT_SCRIPT to the LLaMA converter." >&2
      exit 1
    fi

    convert_cmd=(
      "${PYTHON_EXEC}" "${convert_script}"
      --model_dir "${local_model_dir}"
      --output_dir "${CHECKPOINT_DIR}"
      --dtype "${TRTLLM_DTYPE}"
    )
    if [[ -n ${TP_SIZE:-} ]]; then
      convert_cmd+=(--tp_size "${TP_SIZE}")
    fi
    if [[ -n ${PP_SIZE:-} ]]; then
      convert_cmd+=(--pp_size "${PP_SIZE}")
    fi

    echo "[step:quant] Using converter: ${convert_script}"
    echo "[step:quant] Running: ${convert_cmd[*]}"
    "${convert_cmd[@]}"
  else
    echo "[step:quant] Quantizing to INT4-AWQ..."
    quant_requirements="${TRTLLM_REPO_DIR}/examples/quantization/requirements.txt"
    if [ -f "${quant_requirements}" ]; then
      pip install -r "${quant_requirements}"
      # Upgrade urllib3 to fix GHSA-gm62-xv2j-4w53 and GHSA-2xpw-w6gg-jr37
      pip install 'urllib3>=2.6.0'
    else
      echo "[step:quant] WARNING: quantization requirements.txt not found, continuing"
    fi
    quant_script="${TRTLLM_REPO_DIR}/examples/quantization/quantize.py"
    if [ ! -f "${quant_script}" ]; then
      echo "[step:quant] ERROR: quantize.py not found at ${quant_script}" >&2
      exit 1
    fi
    quant_cmd=(
      "${PYTHON_EXEC}" "${quant_script}"
      --model_dir "${local_model_dir}"
      --output_dir "${CHECKPOINT_DIR}"
      --dtype "${TRTLLM_DTYPE}"
      --qformat int4_awq
      --awq_block_size "${AWQ_BLOCK_SIZE}"
      --calib_size "${CALIB_SIZE}"
      --kv_cache_dtype int8
      --batch_size 16
    )
    echo "[step:quant] Running: ${quant_cmd[*]}"
    "${quant_cmd[@]}"
  fi
fi

echo "[step:quant] Validating checkpoint..."
_validate_downloaded_checkpoint "${CHECKPOINT_DIR}"
echo "[step:quant] OK"
