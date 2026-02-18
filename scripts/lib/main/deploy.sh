#!/usr/bin/env bash
# =============================================================================
# Main Script Deployment Helpers
# =============================================================================
# Functions to log configuration and execute the deployment step sequence.

_MAIN_DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/values/core.sh
source "${_MAIN_DEPLOY_DIR}/../../config/values/core.sh"
# shellcheck source=../../config/patterns.sh
source "${_MAIN_DEPLOY_DIR}/../../config/patterns.sh"

# Log current configuration
log_deploy_config() {
  log_blank
  case "${DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}" in
    "${CFG_DEPLOY_MODE_TOOL}")
      log_info "[main] Configuration: mode=tool, precision=float16"
      log_info "[main] Tool model: ${TOOL_MODEL_NAME:-}"
      ;;
    "${CFG_DEPLOY_MODE_CHAT}")
      log_info "[main] Configuration: mode=chat, engine=${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}, quantization=${QUANT_MODE:-auto}"
      log_info "[main] Chat model: ${CHAT_MODEL_NAME:-}"
      ;;
    *)
      log_info "[main] Configuration: mode=both, engine=${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}, quantization=${QUANT_MODE:-auto}"
      log_info "[main] Chat model: ${CHAT_MODEL_NAME:-}"
      log_info "[main] Tool model: ${TOOL_MODEL_NAME:-}"
      ;;
  esac
}

# Build the deployment command based on engine type and deploy mode
# Usage: build_deploy_cmd <script_dir>
# Returns: deployment command string
build_deploy_cmd() {
  local script_dir="$1"
  local quantizer="quantization/vllm_quantizer.sh"
  local engine_label="vLLM"
  if [ "${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}" = "${CFG_ENGINE_TRT}" ]; then
    quantizer="quantization/trt_quantizer.sh"
    engine_label="TRT"
  fi

  # Tool-only mode: skip Python env verification and quantization (no chat engine needed)
  if [ "${DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    cat <<CMD
      bash '${script_dir}/steps/01_check_gpu.sh' && \\
      bash '${script_dir}/steps/03_install_deps.sh' && \\
      source '${script_dir}/steps/04_env_defaults.sh' && \\
      bash '${script_dir}/steps/05_start_server.sh' && \\
      echo '[main] Deployment process completed successfully' && \\
      echo '[main] Server is running in the background (tool-only mode)' && \\
      echo '[main] Use scripts/stop.sh to stop the server'
CMD
    return
  fi

  cat <<CMD
      bash '${script_dir}/steps/01_check_gpu.sh' && \\
      bash '${script_dir}/steps/02_python_env.sh' && \\
      bash '${script_dir}/steps/03_install_deps.sh' && \\
      source '${script_dir}/steps/04_env_defaults.sh' && \\
      source '${script_dir}/${quantizer}' && \\
      bash '${script_dir}/steps/05_start_server.sh' && \\
      echo '[main] Deployment process completed successfully' && \\
      echo '[main] Server is running in the background (${engine_label} engine)' && \\
      echo '[main] Use scripts/stop.sh to stop the server'
CMD
}

# Export all required environment variables for background process
export_runtime_env() {
  export QUANT_MODE DEPLOY_MODE CHAT_MODEL TOOL_MODEL
  export CHAT_QUANTIZATION INFERENCE_ENGINE
  export CHAT_MODEL_NAME TOOL_MODEL_NAME
}

# Run the deployment pipeline
# Usage: run_deploy <root_dir> <script_dir>
run_deploy() {
  local root_dir="$1"
  local script_dir="$2"
  local deploy_cmd

  deploy_cmd="$(build_deploy_cmd "${script_dir}")"

  export_runtime_env

  run_background \
    "${root_dir}" \
    "${deploy_cmd}" \
    "1" \
    "Starting deployment pipeline in background..."
}
