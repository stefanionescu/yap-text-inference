#!/usr/bin/env bash
# =============================================================================
# Main Script Message Configuration
# =============================================================================
# Canonical user-facing messages for scripts/main.sh.
# shellcheck disable=SC2016

# shellcheck disable=SC2034
readonly -a CFG_MAIN_USAGE_LINES=(
  "Usage:"
  '  $0 [--vllm|--trt] [4bit|8bit] <chat_model> <tool_model> [deploy_mode]'
  '  $0 [--vllm|--trt] [4bit|8bit] chat <chat_model>'
  '  $0 [--vllm|--trt] [4bit|8bit] tool <tool_model>'
  '  $0 [--vllm|--trt] [4bit|8bit] both <chat_model> <tool_model>'
  ""
  "Behavior:"
  "  - Always runs deployment in background (auto-detached)"
  "  - Auto-tails logs (Ctrl+C stops tail, deployment continues)"
  "  - Use scripts/stop.sh to stop the deployment"
  ""
  "Inference Engines:"
  "  --trt       -> Use TensorRT-LLM engine (default, requires CUDA 13.0+)"
  "  --vllm      -> Use vLLM engine"
  "  --engine=X  -> Explicit engine selection (trt or vllm)"
  ""
  "Quantization:"
  "  Omit flag  -> auto-detects GPTQ/AWQ/W4A16 hints; otherwise runs 8bit"
  "  4bit       -> force low-bit chat deployment:"
  "               - vLLM: AWQ or GPTQ depending on the model"
  "               - TRT:  INT4-AWQ quantization"
  "  8bit       -> force 8-bit weight quantization:"
  "               - vLLM: H100/L40/Ada=native FP8, A100=W8A16 emulated"
  "               - TRT:  H100/L40=FP8, A100=INT8-SQ (SmoothQuant)"
  ""
  "Chat model options:"
  "  Float models (8bit auto): SicariusSicariiStuff/Impish_Nemo_12B"
  "                           SicariusSicariiStuff/Wingless_Imp_8B"
  "                           SicariusSicariiStuff/Impish_Mind_8B"
  "                           kyx0r/Neona-12B"
  "  GPTQ models (auto):      SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64"
  "                           SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128"
  "                           SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32"
  "  For awq (float weights): SicariusSicariiStuff/Impish_Nemo_12B"
  "                           SicariusSicariiStuff/Wingless_Imp_8B"
  "                           SicariusSicariiStuff/Impish_Mind_8B"
  "                           kyx0r/Neona-12B"
  ""
  "MoE models:"
  "  Qwen/Qwen3-30B-A3B-Instruct-2507"
  "  ArliAI/Qwen3-30B-A3B-ArliAI-RpR-v4-Fast"
  "  Qwen/Qwen3-Next-80B-A3B-Instruct"
  ""
  "Tool model options:"
  "  yapwithai/yap-longformer-screenshot-intent"
  "  (or any compatible transformers sequence classification repo/path)"
  ""
  "Required environment variables:"
  "  TEXT_API_KEY='secret'             - API authentication key"
  "  HF_TOKEN='hf_xxx'                 - Hugging Face access token"
  "  MAX_CONCURRENT_CONNECTIONS=<int>  - Capacity guard limit"
  ""
  "Environment options:"
  "  DEPLOY_MODE=both|chat|tool    - Which models to deploy (default: both)"
  "  --deploy-mode=both|chat|tool  - CLI override for DEPLOY_MODE"
  "  INFERENCE_ENGINE=trt|vllm     - Inference engine (default: trt)"
  "  GPU_SM_ARCH=sm80|sm89|sm90    - GPU architecture (auto-detected)"
  ""
  "Examples:"
  "  # Standard TensorRT-LLM deployment (default, 4-bit AWQ)"
  '  $0 4bit Qwen/Qwen3-30B-A3B-Instruct-2507 yapwithai/yap-longformer-screenshot-intent'
  ""
  "  # TensorRT-LLM with 8-bit on L40S (FP8)"
  '  $0 8bit SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent'
  ""
  "  # TensorRT-LLM with 8-bit on A100 (INT8-SQ)"
  '  GPU_SM_ARCH=sm80 $0 8bit SicariusSicariiStuff/Impish_Nemo_12B tool_model'
  ""
  "  # vLLM deployment (alternative engine)"
  '  $0 --vllm SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent'
  ""
  "  # 4-bit AWQ for chat (tool model stays float)"
  '  $0 4bit SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent'
  ""
  "  # Chat-only deployment"
  '  $0 chat SicariusSicariiStuff/Impish_Nemo_12B'
  '  DEPLOY_MODE=chat $0 SicariusSicariiStuff/Impish_Nemo_12B'
  ""
  "  # Tool-only deployment"
  '  $0 tool yapwithai/yap-longformer-screenshot-intent'
  '  DEPLOY_MODE=tool $0 yapwithai/yap-longformer-screenshot-intent'
  ""
  "Quantized model uploads (mutually exclusive):"
  "  --push-quant        Upload freshly built 4-bit exports to Hugging Face"
  "  --push-engine       Push locally-built TRT engine to source HF repo"
  "                      Only for prequantized TRT models; adds engine for this GPU"
  "  NOTE: --push-quant and --push-engine cannot be used together"
  ""
  "Debugging:"
  "  --show-hf-logs              Show Hugging Face download/upload progress bars"
  "  --show-trt-logs             Show TensorRT-LLM build/quantization logs"
  "  --show-vllm-logs            Show vLLM engine initialization logs"
  "  --show-llmcompressor-logs   Show LLMCompressor/AutoAWQ calibration progress"
)

# shellcheck disable=SC2034
readonly CFG_MAIN_MSG_INVALID_ARGS="[main] Not enough arguments"
