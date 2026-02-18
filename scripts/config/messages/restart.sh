#!/usr/bin/env bash
# shellcheck disable=SC2034,SC1003
# =============================================================================
# Restart Script Message Configuration
# =============================================================================
# Canonical user-facing messages for scripts/restart.sh and restart helpers.
[[ -n ${_CFG_MSG_RESTART_LOADED:-} ]] && return 0
_CFG_MSG_RESTART_LOADED=1

readonly -a CFG_RESTART_USAGE_LINES=(
  "Usage:"
  "  restart.sh <deploy_mode> [--install-deps] [--keep-models]"
  "  restart.sh <deploy_mode> [--trt|--vllm] [--install-deps] [--keep-models]  # chat/both only"
  "      Quick restart that reuses existing quantized caches (default behavior)."
  "      NOTE: deploy_mode (both|chat|tool) is REQUIRED."
  ""
  '  restart.sh --reset-models --deploy-mode both \'
  '             --chat-model <repo_or_path> --tool-model <repo_or_path> \'
  '             [--trt|--vllm] [--chat-quant 4bit|8bit|fp8|gptq|gptq_marlin|awq] \'
  "             [--install-deps]"
  "      Reconfigure which models/quantization are deployed without reinstalling deps."
  ""
  "Inference Engines (chat/both only):"
  "  --trt           Use TensorRT-LLM engine (default)"
  "  --vllm          Use vLLM engine"
  "  --engine=X      Explicit engine selection (trt or vllm)"
  "  NOTE: tool-only mode rejects engine flags"
  ""
  "  NOTE: Switching engines (trt <-> vllm) triggers FULL environment wipe:"
  "        all HF caches, pip deps, quantized models, and engine artifacts."
  ""
  "Deploy modes (REQUIRED):"
  "  both            - Deploy chat + tool engines"
  "  chat            - Deploy chat-only"
  "  tool            - Deploy tool-only"
  ""
  "Key flags:"
  "  --install-deps        Reinstall dependencies inside .venv before restart"
  "  --reset-models        Delete cached models/HF data and redeploy new models"
  "  --keep-models         Reuse existing quantized caches (default)"
  ""
  "HuggingFace uploads (mutually exclusive):"
  "  --push-quant          Upload cached 4-bit exports to Hugging Face before relaunch"
  "  --push-engine         Push locally-built TRT engine to source HF repo (prequant models only)"
  "  NOTE: --push-quant and --push-engine cannot be used together"
  "  --chat-model <repo>   Chat model to deploy (required with --reset-models chat/both)"
  "  --tool-model <repo>   Tool model to deploy (required with --reset-models tool/both)"
  "  --chat-quant <val>    Override chat/base quantization (4bit|8bit|fp8|gptq|gptq_marlin|awq)."
  "                        4bit uses NVFP4 for MoE models (TRT) or AWQ for dense models."
  "                        8bit uses FP8 (L40S/H100) or INT8-SQ (A100)."
  "                        Pre-quantized repos are detected automatically."
  "  --show-hf-logs              Show Hugging Face download/upload progress bars"
  "  --show-trt-logs             Show TensorRT-LLM build/quantization logs"
  "  --show-vllm-logs            Show vLLM engine initialization logs"
  "  --show-llmcompressor-logs   Show LLMCompressor/AutoAWQ calibration progress"
  ""
  "This script always:"
  "  - Stops the server"
  "  - Preserves the repository and container"
  "  - Keeps dependencies unless --install-deps or stop.sh removes them"
  ""
  "Required environment variables:"
  "  TEXT_API_KEY, HF_TOKEN, MAX_CONCURRENT_CONNECTIONS"
  ""
  "Examples:"
  "  bash scripts/restart.sh both             # TRT engine with existing caches"
  "  bash scripts/restart.sh --vllm both      # Switch to vLLM (triggers full wipe)"
  "  bash scripts/restart.sh chat             # Chat-only restart"
  "  bash scripts/restart.sh tool --install-deps  # Tool-only with deps reinstall"
  '  bash scripts/restart.sh --reset-models \'
  '       --deploy-mode both \'
  '       --chat-model SicariusSicariiStuff/Impish_Nemo_12B \'
  '       --tool-model yapwithai/yap-longformer-screenshot-intent \'
  "       --chat-quant 8bit"
)

readonly CFG_RESTART_MSG_ENGINE_SWITCH_FAILED="[restart] Engine switch failed"
readonly CFG_RESTART_MSG_INVALID_DEPLOY_MODE="[restart] Invalid deploy mode '%s'."
readonly CFG_RESTART_MSG_NO_VENV="[restart] No virtual environment found at %s"
readonly CFG_RESTART_MSG_NO_VENV_HINT="[restart] Run with --install-deps to create it, or run full deployment first"

readonly CFG_RESTART_ERR_PREQUANT_PUSH_QUANT="[restart] Cannot use --push-quant with a prequantized model."
readonly CFG_RESTART_ERR_PREQUANT_MODEL_IS_QUANTIZED="[restart]   Model '%s' is already quantized."
readonly CFG_RESTART_ERR_PREQUANT_NO_ARTIFACTS="[restart]   There are no local quantization artifacts to upload."
readonly CFG_RESTART_ERR_PREQUANT_OPTION_1="[restart]     1. Remove --push-quant to use the prequantized model directly"
readonly CFG_RESTART_ERR_PREQUANT_OPTION_2="[restart]     2. Use a base (non-quantized) model if you want to quantize and push"

readonly CFG_RESTART_ERR_AWQ_NOT_FOUND="[restart] No AWQ models found for deploy mode '%s'"
readonly CFG_RESTART_ERR_AWQ_OPTION_1="[restart]   1. Run full deployment first: bash scripts/main.sh 4bit <chat_model> <tool_model>"
readonly CFG_RESTART_ERR_AWQ_OPTION_2="[restart]   2. Ensure cached AWQ exports exist in %s/.awq/"

readonly CFG_RESTART_ERR_TRT_ENGINE_MISSING="[restart] TRT engine directory not found or not set."
readonly CFG_RESTART_ERR_TRT_ENGINE_DIR="[restart]   TRT_ENGINE_DIR='%s'"
readonly CFG_RESTART_ERR_TRT_ENGINE_OPTION_1="[restart]     1. Build TRT engine first: bash scripts/quantization/trt_quantizer.sh <model>"
readonly CFG_RESTART_ERR_TRT_ENGINE_OPTION_2="[restart]     2. Use vLLM instead: bash scripts/restart.sh --vllm %s"
readonly CFG_RESTART_ERR_TRT_ENGINE_OPTION_3="[restart]     3. Or run full deployment: bash scripts/main.sh --trt <deploy_mode> <model>"
