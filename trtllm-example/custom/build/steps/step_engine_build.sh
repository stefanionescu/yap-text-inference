#!/usr/bin/env bash
set -euo pipefail

source "custom/lib/common.sh"
load_env_if_present
load_environment "$@"
source "custom/build/helpers.sh"

echo "[step:engine] Engine build..."

VENV_DIR="${VENV_DIR:-$PWD/.venv}"
if [ -d "$VENV_DIR" ]; then
  # shellcheck disable=SC1090,SC1091
  source "$VENV_DIR/bin/activate"
fi

ENGINE_OUTPUT_DIR="${TRTLLM_ENGINE_DIR:-$PWD/models/orpheus-trt-awq}"
CHECKPOINT_DIR="${CHECKPOINT_DIR:-$PWD/models/orpheus-trtllm-ckpt-int4-awq}"
TRTLLM_MAX_BATCH_SIZE="${TRTLLM_MAX_BATCH_SIZE:-16}"
TRTLLM_MAX_INPUT_LEN="${TRTLLM_MAX_INPUT_LEN:-48}"
TRTLLM_MAX_OUTPUT_LEN="${TRTLLM_MAX_OUTPUT_LEN:-1162}"
TRTLLM_DTYPE="${TRTLLM_DTYPE:-float16}"
PYTHON_EXEC="${PYTHON_EXEC:-python}"
PRECISION_MODE="${ORPHEUS_PRECISION_MODE:-quantized}"
AWQ_BLOCK_SIZE="${AWQ_BLOCK_SIZE:-128}"
CALIB_SIZE="${CALIB_SIZE:-256}"

if [[ -d ${ENGINE_OUTPUT_DIR} && ${FORCE_REBUILD:-false} != true ]]; then
  echo "[step:engine] Reusing existing engine at ${ENGINE_OUTPUT_DIR}"
else
  if [[ ${PRECISION_MODE} == "base" ]]; then
    echo "[step:engine] Building TensorRT engine (base ${TRTLLM_DTYPE})..."
  else
    echo "[step:engine] Building TensorRT INT4-AWQ engine..."
  fi
  build_cmd=(
    trtllm-build
    --checkpoint_dir "${CHECKPOINT_DIR}"
    --output_dir "${ENGINE_OUTPUT_DIR}"
    --gemm_plugin auto
    --gpt_attention_plugin float16
    --context_fmha enable
    --paged_kv_cache enable
    --remove_input_padding enable
    --max_input_len "${TRTLLM_MAX_INPUT_LEN}"
    --max_seq_len "$((TRTLLM_MAX_INPUT_LEN + TRTLLM_MAX_OUTPUT_LEN))"
    --max_batch_size "${TRTLLM_MAX_BATCH_SIZE}"
    --log_level info
    --workers "$(nproc --all)"
  )
  echo "[step:engine] Running: ${build_cmd[*]}"
  "${build_cmd[@]}"

  echo "[step:engine] Recording build command and metadata..."
  mkdir -p "${ENGINE_OUTPUT_DIR}"
  cmd_file="${ENGINE_OUTPUT_DIR}/build_command.sh"
  printf "#!/usr/bin/env bash\n%s\n" "${build_cmd[*]}" >"$cmd_file"
  chmod +x "$cmd_file"

  default_trtllm_ver="${DEFAULT_TRTLLM_VERSION:-1.2.0rc4}"
  trtllm_ver="$(
    ${PYTHON_EXEC} - <<'PY' 2>/dev/null | tail -1 | tr -d '[:space:]'
import importlib.metadata as md
candidates = ("tensorrt-llm", "tensorrt_llm")
for name in candidates:
    try:
        print(md.version(name))
        break
    except md.PackageNotFoundError:
        continue
else:
    print("")
PY
  )"
  if [ -z "$trtllm_ver" ]; then
    trtllm_ver="$default_trtllm_ver"
  fi

  tensorrt_ver="$(
    ${PYTHON_EXEC} - <<'PY' 2>/dev/null | tail -1 | tr -d '[:space:]'
import importlib.metadata as md
candidates = (
    "tensorrt-cu12-bindings",
    "tensorrt-cu12-libs",
    "tensorrt-cu12-bindings",
    "tensorrt-cu12-libs",
    "tensorrt",
    "nvidia-tensorrt",
)
for name in candidates:
    try:
        print(md.version(name))
        break
    except md.PackageNotFoundError:
        continue
else:
    print("")
PY
  )"
  if [ -z "$tensorrt_ver" ]; then
    tensorrt_ver="unknown"
  fi

  cuda_ver="$(detect_cuda_version)"
  sm_tag="${GPU_SM_ARCH:-unknown}"
  gpu_name="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 || true)"

  if [[ ${PRECISION_MODE} == "base" ]]; then
    quantization_meta="  \"quantization\": {\"weights\": \"${TRTLLM_DTYPE}\", \"kv_cache\": \"${TRTLLM_DTYPE}\"},"
  else
    quantization_meta="  \"quantization\": {\"weights\": \"int4_awq\", \"kv_cache\": \"int8\", \"awq_block_size\": ${AWQ_BLOCK_SIZE}, \"calib_size\": ${CALIB_SIZE}},"
  fi

  meta_file="${ENGINE_OUTPUT_DIR}/build_metadata.json"
  cat >"$meta_file" <<META
{
  "model_id": "${MODEL_ID}",
  "dtype": "${TRTLLM_DTYPE}",
  "max_batch_size": ${TRTLLM_MAX_BATCH_SIZE},
  "max_input_len": ${TRTLLM_MAX_INPUT_LEN},
  "max_output_len": ${TRTLLM_MAX_OUTPUT_LEN},
  "precision_mode": "${PRECISION_MODE}",
${quantization_meta}
  "tensorrt_llm_version": "${trtllm_ver}",
  "tensorrt_version": "${tensorrt_ver}",
  "cuda_toolkit": "${cuda_ver}",
  "sm_arch": "${sm_tag}",
  "gpu_name": "${gpu_name}",
  "build_command": "${build_cmd[*]}"
}
META

  # Copy generation_config.json from HF model to silence TRT-LLM warning
  hf_model_dir="${PWD}/models/$(basename "${MODEL_ID}")-hf"
  if [[ -f "${hf_model_dir}/generation_config.json" ]]; then
    cp "${hf_model_dir}/generation_config.json" "${ENGINE_OUTPUT_DIR}/"
    echo "[step:engine] Copied generation_config.json to engine directory"
  fi
fi

_validate_engine
_record_engine_dir_env "${ENGINE_OUTPUT_DIR}"

echo "[step:engine] OK"
