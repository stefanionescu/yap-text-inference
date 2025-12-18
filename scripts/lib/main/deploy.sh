#!/usr/bin/env bash
# Deployment execution for main.sh
#
# Functions to log configuration and build the deployment command.

# Log current configuration
main_log_config() {
  if [ "${DEPLOY_MODE_SELECTED}" = "tool" ]; then
    log_info "[main] Configuration: quantization=tool-only (classifier runs float16)"
  else
    log_info "[main] Configuration: engine=${INFERENCE_ENGINE}, quantization=${QUANT_MODE:-auto} (backend=${QUANTIZATION:-<unset>}, flag=${QUANT_TYPE})"
  fi
  log_info "[main] Deploy mode: ${DEPLOY_MODE}"
  if [ "${DEPLOY_MODE}" != "tool" ]; then
    log_info "[main] Chat model: ${CHAT_MODEL_NAME}"
    if model_detect_is_moe "${CHAT_MODEL_NAME}"; then
      log_info "[main]   (MoE model detected)"
    fi
  fi
  if [ "${DEPLOY_MODE}" != "chat" ]; then
    log_info "[main] Tool model: ${TOOL_MODEL_NAME}"
  fi
  log_info ""
  log_info "[main] Starting deployment in background (auto-detached)"
  log_info "[main] Ctrl+C stops log tailing only - deployment continues"
  log_info "[main] Use scripts/stop.sh to stop the deployment"
}

# Build the deployment command based on engine type
# Usage: main_build_deploy_cmd <script_dir>
# Returns: deployment command string
main_build_deploy_cmd() {
  local script_dir="$1"
  local cmd=""

  if [ "${INFERENCE_ENGINE}" = "trt" ]; then
    # TensorRT-LLM pipeline
    cmd="
      bash '${script_dir}/steps/01_check_gpu.sh' && \\
      bash '${script_dir}/steps/02_python_env.sh' && \\
      bash '${script_dir}/steps/03_install_deps.sh' && \\
      source '${script_dir}/steps/04_env_defaults.sh' && \\
      source '${script_dir}/quantization/trt_quantizer.sh' && \\
      bash '${script_dir}/steps/05_start_server.sh' && \\
      echo '[main] Deployment process completed successfully' && \\
      echo '[main] Server is running in the background (TRT engine)' && \\
      echo '[main] Use scripts/stop.sh to stop the server'
    "
  else
    # vLLM pipeline
    cmd="
      bash '${script_dir}/steps/01_check_gpu.sh' && \\
      bash '${script_dir}/steps/02_python_env.sh' && \\
      bash '${script_dir}/steps/03_install_deps.sh' && \\
      source '${script_dir}/steps/04_env_defaults.sh' && \\
      source '${script_dir}/quantization/vllm_quantizer.sh' && \\
      bash '${script_dir}/steps/05_start_server.sh' && \\
      echo '[main] Deployment process completed successfully' && \\
      echo '[main] Server is running in the background (vLLM engine)' && \\
      echo '[main] Use scripts/stop.sh to stop the server'
    "
  fi

  echo "${cmd}"
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

