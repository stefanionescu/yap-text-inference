#!/usr/bin/env bash
# =============================================================================
# Main Script Deployment Helpers
# =============================================================================
# Functions to log configuration and execute the deployment step sequence.

# Log current configuration
main_log_config() {
  log_blank
  if [ "${DEPLOY_MODE:-}" = "tool" ]; then
    log_info "[main] Configuration:, tool-only, precision=float16"
  else
    log_info "[main] Configuration: engine=${INFERENCE_ENGINE:-vllm}, quantization=${QUANT_MODE:-auto}"
  fi
  log_info "[main] Deploy mode: ${DEPLOY_MODE:-both}"
  if [ "${DEPLOY_MODE:-}" != "tool" ]; then
    log_info "[main] Chat model: ${CHAT_MODEL_NAME:-}"
  fi
  if [ "${DEPLOY_MODE:-}" != "chat" ]; then
    log_info "[main] Tool model: ${TOOL_MODEL_NAME:-}"
  fi
}

# Build the deployment command based on engine type
# Usage: main_build_deploy_cmd <script_dir>
# Returns: deployment command string
main_build_deploy_cmd() {
  local script_dir="$1"
  local quantizer="quantization/vllm_quantizer.sh"
  local engine_label="vLLM"
  if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ]; then
    quantizer="quantization/trt_quantizer.sh"
    engine_label="TRT"
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
main_export_all() {
  export QUANTIZATION QUANT_MODE DEPLOY_MODE CHAT_MODEL TOOL_MODEL
  export CHAT_QUANTIZATION INFERENCE_ENGINE
  export CHAT_MODEL_NAME TOOL_MODEL_NAME
}

# Run the deployment pipeline
# Usage: main_run_deploy <root_dir> <script_dir>
main_run_deploy() {
  local root_dir="$1"
  local script_dir="$2"
  local deploy_cmd
  
  deploy_cmd="$(main_build_deploy_cmd "${script_dir}")"
  
  main_export_all
  
  runtime_pipeline_run_background \
    "${root_dir}" \
    "${deploy_cmd}" \
    "1" \
    "Starting deployment pipeline in background..."
}
