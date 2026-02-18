#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Server Restart Script
# =============================================================================
# Restarts the inference server with optional model/quantization reconfiguration.
# Supports quick restart (reusing caches) or full reconfiguration with new models.
#
# Usage: bash scripts/restart.sh <deploy_mode> [options]
# See usage() below for full options.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # sourced helpers rely on ROOT_DIR
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/lib/noise/python.sh"
source "${SCRIPT_DIR}/lib/common/log.sh"
source "${SCRIPT_DIR}/lib/common/params.sh"
source "${SCRIPT_DIR}/lib/common/warmup.sh"
source "${SCRIPT_DIR}/lib/deps/venv/main.sh"
source "${SCRIPT_DIR}/lib/runtime/restart_guard.sh"
source "${SCRIPT_DIR}/lib/runtime/pipeline.sh"
source "${SCRIPT_DIR}/lib/common/model_validate.sh"
source "${SCRIPT_DIR}/lib/common/cli.sh"
source "${SCRIPT_DIR}/lib/common/pytorch_guard.sh"
source "${SCRIPT_DIR}/lib/restart/overrides.sh"
source "${SCRIPT_DIR}/lib/restart/args.sh"
source "${SCRIPT_DIR}/lib/restart/basic.sh"
source "${SCRIPT_DIR}/lib/restart/reconfigure/run.sh"
source "${SCRIPT_DIR}/lib/restart/awq.sh"
source "${SCRIPT_DIR}/lib/restart/errors.sh"
source "${SCRIPT_DIR}/lib/env/restart.sh"
source "${SCRIPT_DIR}/lib/restart/launch.sh"
source "${SCRIPT_DIR}/lib/restart/pipeline.sh"
source "${SCRIPT_DIR}/engines/vllm/push.sh"
source "${SCRIPT_DIR}/engines/trt/push.sh"
source "${SCRIPT_DIR}/engines/trt/detect.sh"
source "${SCRIPT_DIR}/lib/common/gpu_detect.sh"
source "${SCRIPT_DIR}/lib/common/cuda.sh"

usage() {
  cat <<'USAGE'
Usage:
  restart.sh <deploy_mode> [--trt|--vllm] [--install-deps] [--keep-models]
      Quick restart that reuses existing quantized caches (default behavior).
      NOTE: deploy_mode (both|chat|tool) is REQUIRED.

  restart.sh --reset-models --deploy-mode both \
             --chat-model <repo_or_path> --tool-model <repo_or_path> \
             [--trt|--vllm] [--chat-quant 4bit|8bit|fp8|gptq|gptq_marlin|awq] \
             [--install-deps]
      Reconfigure which models/quantization are deployed without reinstalling deps.

Inference Engines:
  --trt           Use TensorRT-LLM engine (default)
  --vllm          Use vLLM engine
  --engine=X      Explicit engine selection (trt or vllm)

  NOTE: Switching engines (trt <-> vllm) triggers FULL environment wipe:
        all HF caches, pip deps, quantized models, and engine artifacts.

Deploy modes (REQUIRED):
  both            - Deploy chat + tool engines
  chat            - Deploy chat-only
  tool            - Deploy tool-only

Key flags:
  --install-deps        Reinstall dependencies inside .venv before restart
  --reset-models        Delete cached models/HF data and redeploy new models
  --keep-models         Reuse existing quantized caches (default)

HuggingFace uploads (mutually exclusive):
  --push-quant          Upload cached 4-bit exports to Hugging Face before relaunch
  --push-engine         Push locally-built TRT engine to source HF repo (prequant models only)
  NOTE: --push-quant and --push-engine cannot be used together
  --chat-model <repo>   Chat model to deploy (required with --reset-models chat/both)
  --tool-model <repo>   Tool model to deploy (required with --reset-models tool/both)
  --chat-quant <val>    Override chat/base quantization (4bit|8bit|fp8|gptq|gptq_marlin|awq).
                        `4bit` uses NVFP4 for MoE models (TRT) or AWQ for dense models.
                        `8bit` uses FP8 (L40S/H100) or INT8-SQ (A100).
                        Pre-quantized repos are detected automatically.
  --show-hf-logs              Show Hugging Face download/upload progress bars
  --show-trt-logs             Show TensorRT-LLM build/quantization logs
  --show-vllm-logs            Show vLLM engine initialization logs
  --show-llmcompressor-logs   Show LLMCompressor/AutoAWQ calibration progress

This script always:
  • Stops the server
  • Preserves the repository and container
  • Keeps dependencies unless --install-deps or stop.sh removes them

Required environment variables:
  TEXT_API_KEY, HF_TOKEN, MAX_CONCURRENT_CONNECTIONS

Examples:
  bash scripts/restart.sh both             # TRT engine with existing caches
  bash scripts/restart.sh --vllm both      # Switch to vLLM (triggers full wipe)
  bash scripts/restart.sh chat             # Chat-only restart
  bash scripts/restart.sh tool --install-deps  # Tool-only with deps reinstall
  bash scripts/restart.sh --reset-models \
       --deploy-mode both \
       --chat-model SicariusSicariiStuff/Impish_Nemo_12B \
       --tool-model yapwithai/yap-longformer-screenshot-intent \
       --chat-quant 8bit
USAGE
  exit 1
}

restart_main "$@"
