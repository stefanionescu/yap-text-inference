#!/usr/bin/env bash
set -euo pipefail

source "scripts/lib/common.sh"
load_env_if_present
load_environment
source "scripts/build/helpers.sh"

echo "[build:quantize] Preparing checkpoint..."

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
CALIB_SIZE="${CALIB_SIZE:-32}"
PRECISION_MODE="${ORPHEUS_PRECISION_MODE:-quantized}"

if [[ ${SKIP_QUANTIZATION:-false} == true ]]; then
  echo "[build:quantize] Skipping checkpoint prep (provided checkpoint)"
  _validate_downloaded_checkpoint "${CHECKPOINT_DIR}"
  exit 0
fi

export HF_HUB_ENABLE_HF_TRANSFER=1

_prepare_model_repo() {
  local model_path="${MODEL_ID}"
  if [[ -z ${model_path} ]]; then
    echo "[build:quantize] ERROR: MODEL_ID unset" >&2
    return 1
  fi
  if [[ -d ${model_path} ]]; then
    echo "[build:quantize] Using local model directory: ${model_path}" >&2
    echo "${model_path}"
    return 0
  fi
  local target
  target="${PWD}/models/$(basename "${model_path}")-hf"
  if [[ ! -d ${target} ]]; then
    echo "[build:quantize] Downloading model from HuggingFace: ${model_path}" >&2
    mkdir -p "${target}"
    "${PYTHON_EXEC}" -c "
from huggingface_hub import snapshot_download
snapshot_download(repo_id='${model_path}', local_dir='${target}')
print('[build:quantize] Downloaded complete model repository')
" >&2
  else
    echo "[build:quantize] Using cached HF model at ${target}" >&2
  fi
  echo "${target}"
}

if [[ -d ${CHECKPOINT_DIR} && ${FORCE_REBUILD:-false} != true ]]; then
  echo "[build:quantize] Reusing existing checkpoint at ${CHECKPOINT_DIR}"
else
  rm -rf "${CHECKPOINT_DIR}"
  mkdir -p "${CHECKPOINT_DIR}"
  local_model_dir="$(_prepare_model_repo)"
  if [[ -z ${local_model_dir} ]]; then
    echo "[build:quantize] ERROR: Failed to prepare local model directory" >&2
    exit 1
  fi

  # Install quantization requirements (needed for both base and quantized modes)
  # Skip if: INSTALL_DEPS=0 (restart without --install-deps), or marker exists
  quant_deps_marker="${ROOT_DIR:-.}/.run/quant_deps_installed"
  quant_requirements="${TRTLLM_REPO_DIR}/examples/quantization/requirements.txt"
  if [ "${INSTALL_DEPS:-1}" = "0" ]; then
    echo "[build:quantize] Skipping quantization deps (INSTALL_DEPS=0)"
  elif [ -f "${quant_deps_marker}" ] && [ "${FORCE_INSTALL_DEPS:-0}" != "1" ]; then
    echo "[build:quantize] Quantization deps already installed, skipping"
  elif [ -f "${quant_requirements}" ]; then
    echo "[build:quantize] Installing quantization requirements..."
    pip install -r "${quant_requirements}"
    # Upgrade urllib3 to fix GHSA-gm62-xv2j-4w53 and GHSA-2xpw-w6gg-jr37
    pip install 'urllib3>=2.6.0'
    # Mark as installed
    mkdir -p "$(dirname "$quant_deps_marker")"
    date -u +%Y-%m-%dT%H:%M:%SZ > "$quant_deps_marker"
  else
    echo "[build:quantize] WARNING: quantization requirements.txt not found, continuing"
  fi

  quant_script="${TRTLLM_REPO_DIR}/examples/quantization/quantize.py"
  if [ ! -f "${quant_script}" ]; then
    echo "[build:quantize] ERROR: quantize.py not found at ${quant_script}" >&2
    exit 1
  fi

  if [[ ${PRECISION_MODE} == "base" ]]; then
    # Base mode: FP8 on Ada/Hopper, full precision on Ampere
    BASE_QFORMAT="$(_resolve_base_qformat)"
    BASE_KV_CACHE_DTYPE="$(_resolve_base_kv_cache_dtype "${BASE_QFORMAT}")"
    GPU_NAME="$(_detect_gpu_name)"

    if [[ "${BASE_QFORMAT}" == "full_prec" ]]; then
      echo "[build:quantize] Converting to full precision (no quantization)..."
    else
      echo "[build:quantize] Quantizing to ${BASE_QFORMAT}..."
    fi
    [[ -n ${GPU_NAME} ]] && echo "[build:quantize] Detected GPU: ${GPU_NAME}"
    echo "[build:quantize] Using qformat=${BASE_QFORMAT}, kv_cache_dtype=${BASE_KV_CACHE_DTYPE}"

    quant_cmd=(
      "${PYTHON_EXEC}" "${quant_script}"
      --model_dir "${local_model_dir}"
      --output_dir "${CHECKPOINT_DIR}"
      --dtype "${TRTLLM_DTYPE}"
      --qformat "${BASE_QFORMAT}"
    )
    # Only add kv_cache_dtype if not "none" (full_prec uses model dtype)
    if [[ "${BASE_KV_CACHE_DTYPE}" != "none" ]]; then
      quant_cmd+=(--kv_cache_dtype "${BASE_KV_CACHE_DTYPE}")
    fi
    # Only add calib_size if actually quantizing (not full_prec)
    if [[ "${BASE_QFORMAT}" != "full_prec" ]]; then
      quant_cmd+=(--calib_size "${CALIB_SIZE}" --batch_size 16)
    fi
    if [[ -n ${TP_SIZE:-} ]]; then
      quant_cmd+=(--tp_size "${TP_SIZE}")
    fi
    if [[ -n ${PP_SIZE:-} ]]; then
      quant_cmd+=(--pp_size "${PP_SIZE}")
    fi

    echo "[build:quantize] Running: ${quant_cmd[*]}"
    "${quant_cmd[@]}"
  else
    # Quantized mode: INT4-AWQ (default)
    echo "[build:quantize] Quantizing to INT4-AWQ..."
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
    if [[ -n ${TP_SIZE:-} ]]; then
      quant_cmd+=(--tp_size "${TP_SIZE}")
    fi
    if [[ -n ${PP_SIZE:-} ]]; then
      quant_cmd+=(--pp_size "${PP_SIZE}")
    fi

    echo "[build:quantize] Running: ${quant_cmd[*]}"
    "${quant_cmd[@]}"
  fi
fi

echo "[build:quantize] Validating checkpoint..."
_validate_downloaded_checkpoint "${CHECKPOINT_DIR}"

# Export resolved qformat for downstream metadata (step_engine_build.sh)
if [[ ${PRECISION_MODE} == "base" ]]; then
  mkdir -p .run
  echo "RESOLVED_QFORMAT=${BASE_QFORMAT:-$(_resolve_base_qformat)}" > .run/quantize_result.env
  echo "RESOLVED_KV_DTYPE=${BASE_KV_CACHE_DTYPE:-$(_resolve_base_kv_cache_dtype)}" >> .run/quantize_result.env
fi

echo "[build:quantize] OK"
