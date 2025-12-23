#!/usr/bin/env bash
# AWQ Docker image environment defaults (wraps scripts/lib/environment.sh)

export ORPHEUS_ENV_ROOT=${ORPHEUS_ENV_ROOT:-/app}
export ORPHEUS_MODELS_DIR_DEFAULT=${ORPHEUS_MODELS_DIR_DEFAULT:-/opt/models}
export ORPHEUS_ENGINES_DIR_DEFAULT=${ORPHEUS_ENGINES_DIR_DEFAULT:-/opt/engines}
export ORPHEUS_CHECKPOINT_BASE_DEFAULT=${ORPHEUS_CHECKPOINT_BASE_DEFAULT:-/opt/models/orpheus-trtllm-ckpt-8bit}
export ORPHEUS_CHECKPOINT_QUANT_DEFAULT=${ORPHEUS_CHECKPOINT_QUANT_DEFAULT:-/opt/models/orpheus-trtllm-ckpt-int4-awq}
export ORPHEUS_ENGINE_BASE_DEFAULT=${ORPHEUS_ENGINE_BASE_DEFAULT:-/opt/engines/orpheus-trt-8bit}
export ORPHEUS_ENGINE_QUANT_DEFAULT=${ORPHEUS_ENGINE_QUANT_DEFAULT:-/opt/engines/orpheus-trt-awq}
export ORPHEUS_HF_DEPLOY_WORKDIR_DEFAULT=${ORPHEUS_HF_DEPLOY_WORKDIR_DEFAULT:-/opt/models/_hf_download}
export ORPHEUS_TRTLLM_REPO_DEFAULT=${ORPHEUS_TRTLLM_REPO_DEFAULT:-/app/.trtllm-repo}
export HF_DEPLOY_REPO_ID=${HF_DEPLOY_REPO_ID:-yapwithai/orpheus-3b-tts-trt-awq}

# shellcheck disable=SC1091
source /app/scripts/lib/environment.sh
