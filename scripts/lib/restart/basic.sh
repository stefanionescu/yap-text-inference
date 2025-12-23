#!/usr/bin/env bash

# Generic (non-AWQ) restart path for scripts/restart.sh
# Requires: SCRIPT_DIR, ROOT_DIR

# Wipe all pip/venv dependencies and caches for a clean reinstall
# Preserves: HF cache, TRT repo, models, AWQ cache, quantized engines
# This is ONLY called when --install-deps is passed (explicit user request)
wipe_dependencies_for_reinstall() {
  local root="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  
  log_info "[deps] Wiping all dependencies for clean reinstall (--install-deps)..."
  
  # 1. Remove all venvs (all pip packages gone)
  # This is intentional - user explicitly requested --install-deps
  for venv_path in "${root}/.venv" "${root}/.venv-trt" "${root}/.venv-vllm" "${root}/venv" "${root}/env"; do
    if [ -d "${venv_path}" ]; then
      log_info "[deps] Removing venv: ${venv_path}"
      rm -rf "${venv_path}"
    fi
  done
  
  # 2. Remove pip caches (wheels, downloaded packages)
  for pip_cache in "${root}/.pip_cache" "$HOME/.cache/pip" "/root/.cache/pip" "/workspace/.cache/pip"; do
    if [ -d "${pip_cache}" ]; then
      log_info "[deps] Removing pip cache: ${pip_cache}"
      rm -rf "${pip_cache}"
    fi
  done
  
  # 3. Remove vLLM-specific caches
  local VLLM_CACHES=(
    "${root}/.flashinfer"
    "${root}/.xformers"
    "${root}/.vllm_cache"
    "$HOME/.cache/flashinfer" "/root/.cache/flashinfer"
    "$HOME/.cache/vllm" "/root/.cache/vllm"
    "/workspace/.cache/vllm"
  )
  for cache_dir in "${VLLM_CACHES[@]}"; do
    if [ -d "${cache_dir}" ]; then
      log_info "[deps] Removing vLLM cache: ${cache_dir}"
      rm -rf "${cache_dir}"
    fi
  done
  
  # 4. Remove TRT-LLM specific caches (wheel caches, compiled engines metadata)
  local TRT_CACHES=(
    "${root}/.trt_cache"
    "$HOME/.cache/tensorrt_llm" "/root/.cache/tensorrt_llm"
    "$HOME/.cache/tensorrt" "/root/.cache/tensorrt"
    "$HOME/.cache/nvidia" "/root/.cache/nvidia"
    "$HOME/.cache/modelopt" "/root/.cache/modelopt"
    "$HOME/.cache/onnx" "/root/.cache/onnx"
    "$HOME/.cache/cuda" "/root/.cache/cuda"
    "$HOME/.cache/pycuda" "/root/.cache/pycuda"
    "$HOME/.local/share/tensorrt_llm" "/root/.local/share/tensorrt_llm"
    "/workspace/.cache/tensorrt" "/workspace/.cache/tensorrt_llm"
  )
  for cache_dir in "${TRT_CACHES[@]}"; do
    if [ -d "${cache_dir}" ]; then
      log_info "[deps] Removing TRT cache: ${cache_dir}"
      rm -rf "${cache_dir}"
    fi
  done
  
  # 5. Remove torch/compiler caches (triton, inductor, extensions)
  local COMPILER_CACHES=(
    "${root}/.torch_inductor"
    "${root}/.triton"
    "$HOME/.cache/torch" "/root/.cache/torch"
    "$HOME/.cache/torch_extensions" "/root/.cache/torch_extensions"
    "$HOME/.triton" "/root/.triton"
    "$HOME/.torch_inductor" "/root/.torch_inductor"
    "/workspace/.cache/torch" "/workspace/.cache/triton"
  )
  for cache_dir in "${COMPILER_CACHES[@]}"; do
    if [ -d "${cache_dir}" ]; then
      log_info "[deps] Removing compiler cache: ${cache_dir}"
      rm -rf "${cache_dir}"
    fi
  done
  
  # 6. Remove NVIDIA JIT caches
  for nv_cache in "$HOME/.nv" "/root/.nv"; do
    if [ -d "${nv_cache}" ]; then
      log_info "[deps] Removing NVIDIA JIT cache: ${nv_cache}"
      rm -rf "${nv_cache}"
    fi
  done
  
  # 7. Remove dep hash markers (forces full reinstall)
  rm -f "${root}/.venv/.req_hash" 2>/dev/null || true
  rm -f "${root}/.run/trt_quant_deps_installed" 2>/dev/null || true
  
  # 8. Clean temp directories
  rm -rf /tmp/pip-* /tmp/torch_* /tmp/flashinfer* /tmp/triton* /tmp/trt* /tmp/tensorrt* /tmp/nv* /tmp/cuda* 2>/dev/null || true
  
  # 9. Clean shared memory (TRT-LLM uses /dev/shm)
  rm -rf /dev/shm/tensorrt* /dev/shm/trt* /dev/shm/torch* /dev/shm/nv* /dev/shm/cuda* 2>/dev/null || true
  
  log_info "[deps] ✓ All dependency caches wiped. Models, HF cache, TRT repo preserved."
}

# Shared install-deps handler used by both generic and AWQ restart paths
restart_run_install_deps_if_needed() {
  if [ "${INSTALL_DEPS}" != "1" ]; then
    return 0
  fi
  
  log_info "[restart] Reinstalling all dependencies from scratch (--install-deps)"
  
  # Wipe all existing pip dependencies and caches for clean install
  # Preserves models, HF cache, TRT repo (if same engine)
  wipe_dependencies_for_reinstall
  
  # Ensure correct Python version is available (TRT needs 3.10, vLLM uses system python)
  INFERENCE_ENGINE="${INFERENCE_ENGINE:-trt}" "${SCRIPT_DIR}/steps/02_python_env.sh" || {
    log_err "[restart] Failed to set up Python environment"
    exit 1
  }
  
  # Reinstall all dependencies from scratch (force mode)
  FORCE_REINSTALL=1 INFERENCE_ENGINE="${INFERENCE_ENGINE:-trt}" "${SCRIPT_DIR}/steps/03_install_deps.sh"
}

restart_basic() {
  local SERVER_LOG LAST_QUANT LAST_DEPLOY LAST_CHAT LAST_TOOL LAST_ENV_FILE
  SERVER_LOG="${ROOT_DIR}/server.log"
  LAST_QUANT=""; LAST_DEPLOY=""; LAST_CHAT=""; LAST_TOOL=""
  LAST_ENV_FILE="${ROOT_DIR}/.run/last_config.env"

  if [ -f "${SERVER_LOG}" ]; then
    LAST_QUANT=$(grep -E "Quantization: " "${SERVER_LOG}" | tail -n1 | awk -F': ' '{print $2}' | awk '{print $1}' || true)
    LAST_DEPLOY=$(grep -E "Deploy mode: " "${SERVER_LOG}" | tail -n1 | sed -E 's/.*Deploy mode: ([^ ]+).*/\1/' || true)
    LAST_CHAT=$(grep -E "Chat model: " "${SERVER_LOG}" | tail -n1 | sed -E 's/.*Chat model: *(.*)/\1/' || true)
    LAST_TOOL=$(grep -E "Tool model: " "${SERVER_LOG}" | tail -n1 | sed -E 's/.*Tool model: *(.*)/\1/' || true)
    if [ -z "${LAST_CHAT}" ] || [ "${LAST_CHAT}" = "(none)" ]; then
      LAST_CHAT=$(grep -E "CHAT=" "${SERVER_LOG}" | tail -n1 | sed -E 's/.*CHAT=([^ ]*).*/\1/' || true)
      # Fallback to MODEL= line when deploying chat-only
      if [ -z "${LAST_CHAT}" ]; then
        LAST_CHAT=$(grep -E "MODEL=" "${SERVER_LOG}" | tail -n1 | sed -E 's/.*MODEL=([^ ]*).*/\1/' || true)
      fi
    fi
    if [ -z "${LAST_TOOL}" ] || [ "${LAST_TOOL}" = "(none)" ]; then
      LAST_TOOL=$(grep -E "TOOL=" "${SERVER_LOG}" | tail -n1 | sed -E 's/.*TOOL=([^ ]*).*/\1/' || true)
    fi
  fi

  if [ -z "${LAST_QUANT}" ] && [ -f "${LAST_ENV_FILE}" ]; then
    # shellcheck disable=SC1090
    source "${LAST_ENV_FILE}" || true
    LAST_QUANT="${LAST_QUANT:-${QUANTIZATION:-}}"
    LAST_DEPLOY="${LAST_DEPLOY:-${DEPLOY_MODE:-}}"
    LAST_CHAT="${LAST_CHAT:-${CHAT_MODEL:-}}"
    LAST_TOOL="${LAST_TOOL:-${TOOL_MODEL:-}}"
  fi


  # If the last snapshot stored explicit per-engine quantization, prefer that over
  # the generic fallback so we don't misclassify AWQ/GPTQ deployments as 8bit.
  local LAST_CHAT_QUANT="${CHAT_QUANTIZATION:-}"
  if [ -z "${LAST_QUANT}" ] || [ "${LAST_QUANT}" = "fp8" ] || [ "${LAST_QUANT}" = "8bit" ]; then
    if [ -n "${LAST_CHAT_QUANT}" ] && [ "${LAST_CHAT_QUANT}" != "fp8" ] && [ "${LAST_CHAT_QUANT}" != "8bit" ]; then
      LAST_QUANT="${LAST_CHAT_QUANT}"
    fi
  fi

  local SHOULD_USE_GENERIC=0
  if [ -n "${QUANTIZATION:-}" ] && [ "${QUANTIZATION}" != "awq" ]; then
    SHOULD_USE_GENERIC=1
  elif [ -n "${LAST_QUANT}" ] && [ "${LAST_QUANT}" != "awq" ]; then
    SHOULD_USE_GENERIC=1
  fi

  if [ "${SHOULD_USE_GENERIC}" != "1" ]; then
    return 0
  fi

  # Non-AWQ path
  # shellcheck disable=SC2153  # DEPLOY_MODE is set by the caller via env
  local SELECTED_DEPLOY="${DEPLOY_MODE}"
  if [ -z "${SELECTED_DEPLOY}" ] || ! [[ "${SELECTED_DEPLOY}" =~ ^(both|chat|tool)$ ]]; then
    SELECTED_DEPLOY="${DEPLOY_MODE:-${LAST_DEPLOY:-both}}"
  fi

  if [ "${DEPLOY_MODE}" = "tool" ]; then
    unset QUANTIZATION CHAT_QUANTIZATION
  else
    # Default to "8bit" placeholder; resolved to fp8 or int8 based on GPU in quantization.sh
    export QUANTIZATION="${QUANTIZATION:-${LAST_QUANT:-8bit}}"
  fi
  export DEPLOY_MODE="${SELECTED_DEPLOY}"

  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
    export CHAT_MODEL="${CHAT_MODEL:-${LAST_CHAT:-}}"
  fi
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
    export TOOL_MODEL="${TOOL_MODEL:-${LAST_TOOL:-}}"
  fi

  if [ "${DEPLOY_MODE}" != "tool" ] && [ -z "${CHAT_MODEL:-}" ]; then
    log_err "[restart] CHAT_MODEL is required for DEPLOY_MODE='${DEPLOY_MODE}'"
    [ -f "${SERVER_LOG}" ] && log_err "[restart] Hint: Could not parse chat model from server.log"
    exit 1
  fi
  if [ "${DEPLOY_MODE}" != "chat" ] && [ -z "${TOOL_MODEL:-}" ]; then
    log_err "[restart] TOOL_MODEL is required for DEPLOY_MODE='${DEPLOY_MODE}'"
    [ -f "${SERVER_LOG}" ] && log_err "[restart] Hint: Could not parse tool model from server.log"
    exit 1
  fi

  if [ "${DEPLOY_MODE}" = "tool" ]; then
    log_info "[restart] Quick restart: tool-only classifier deployment"
  else
    log_info "[restart] Quick restart: reusing cached ${QUANTIZATION:-8bit} models (deploy=${DEPLOY_MODE})"
  fi

  # 1. Stop server first (before any deps/env work)
  log_info "[restart] Stopping server (preserving models and dependencies)..."
  NUKE_ALL=0 "${SCRIPT_DIR}/stop.sh"

  # 2. Handle --install-deps (wipe and reinstall all dependencies)
  restart_run_install_deps_if_needed

  # 3. Load environment defaults (after deps are installed)
  log_info "[restart] Loading environment defaults..."
  source "${SCRIPT_DIR}/steps/04_env_defaults.sh"

  # 4. TRT engine: validate engine directory exists before starting server
  if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ] && [ "${DEPLOY_MODE}" != "tool" ]; then
    if [ -z "${TRT_ENGINE_DIR:-}" ] || [ ! -d "${TRT_ENGINE_DIR:-}" ]; then
      log_err "[restart] TRT engine directory not found or not set."
      log_err "[restart] TRT_ENGINE_DIR='${TRT_ENGINE_DIR:-<empty>}'"
      log_err "[restart] "
      log_err "[restart] TensorRT-LLM requires a pre-built engine. Options:"
      log_err "[restart]   1. Build TRT engine first: bash scripts/quantization/trt_quantizer.sh <model>"
      log_err "[restart]   2. Use vLLM instead: bash scripts/restart.sh --vllm ${DEPLOY_MODE}"
      log_err "[restart]   3. Or run full deployment: bash scripts/main.sh --trt <deploy_mode> <model>"
      exit 1
    fi
    log_info "[restart] TRT engine validated: ${TRT_ENGINE_DIR}"
  fi

  local SERVER_LOG_PATH="${ROOT_DIR}/server.log"
  touch "${SERVER_LOG_PATH}"
  if [ "${DEPLOY_MODE}" = "tool" ]; then
    log_info "[restart] Starting server directly with existing models (tool-only classifier deployment)..."
  else
    log_info "[restart] Starting server directly with existing models (quant=${QUANTIZATION})..."
  fi
  log_info "[restart] All logs: tail -f server.log"
  log_info "[restart] To stop: bash scripts/stop.sh"
  log_info ""

  mkdir -p "${ROOT_DIR}/.run"
  setsid nohup "${ROOT_DIR}/scripts/steps/05_start_server.sh" </dev/null >> "${SERVER_LOG_PATH}" 2>&1 &
  local BG_PID=$!
  echo "${BG_PID}" > "${ROOT_DIR}/.run/deployment.pid"

  log_info "[restart] Server started (PID: ${BG_PID})"
  log_info "[restart] Following logs (Ctrl+C detaches, server continues)..."
  exec tail -n +1 -F "${SERVER_LOG_PATH}"
}
