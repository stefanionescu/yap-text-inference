#!/usr/bin/env bash
# Shared env-default initialization for Docker build entrypoints.

# build_init_router_defaults - Initialize shared router defaults for docker/build.sh.
build_init_router_defaults() {
  ENGINE="${ENGINE:-vllm}"
  DEPLOY_MODE="${DEPLOY_MODE:-both}"
}

# build_init_common_defaults - Initialize shared defaults for concrete build entrypoints.
build_init_common_defaults() {
  DOCKER_USERNAME="${DOCKER_USERNAME:-your-username}"
  IMAGE_NAME="${IMAGE_NAME:-yap-text-api}"
  HF_TOKEN="${HF_TOKEN:-}"
}

# build_init_vllm_defaults - Initialize the vLLM build-surface defaults.
build_init_vllm_defaults() {
  build_init_common_defaults
  DEPLOY_MODE_VAL="${DEPLOY_MODE:-both}"
  CHAT_MODEL="${CHAT_MODEL:-}"
  TOOL_MODEL="${TOOL_MODEL:-}"
  CHAT_QUANTIZATION="${CHAT_QUANTIZATION:-}"
  TAG="${TAG:-vllm-${DEPLOY_MODE_VAL}}"
}

# build_init_trt_defaults - Initialize the TRT build-surface defaults.
build_init_trt_defaults() {
  build_init_common_defaults
  DEPLOY_MODE_VAL="${DEPLOY_MODE:-both}"
  CHAT_MODEL="${CHAT_MODEL:-}"
  TOOL_MODEL="${TOOL_MODEL:-}"
  CHAT_QUANTIZATION="${CHAT_QUANTIZATION:-}"
  TRT_ENGINE_REPO="${TRT_ENGINE_REPO:-${CHAT_MODEL}}"
  TRT_ENGINE_LABEL="${TRT_ENGINE_LABEL:-}"
  TAG="${TAG:-trt-${DEPLOY_MODE_VAL}}"
}

# build_init_tool_defaults - Initialize the tool-only build-surface defaults.
build_init_tool_defaults() {
  build_init_common_defaults
  DEPLOY_MODE_VAL="tool"
  TOOL_MODEL="${TOOL_MODEL:-}"
  TAG="${TAG:-tool-only}"
}
