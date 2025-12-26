#!/usr/bin/env bash

# Early model validation before deployment starts
# Calls Python to check models against allowlists without loading heavy vLLM deps

validate_models_early() {
  local deploy_mode="${DEPLOY_MODE:-both}"
  local chat_model="${CHAT_MODEL:-}"
  local tool_model="${TOOL_MODEL:-}"
  local quantization="${QUANTIZATION:-}"
  local chat_quant="${CHAT_QUANTIZATION:-}"
  local engine="${INFERENCE_ENGINE:-${ENGINE_TYPE:-trt}}"

  # Find Python - prefer venv if available
  local python_cmd="python3"
  if [ -f "${ROOT_DIR}/.venv/bin/python" ]; then
    python_cmd="${ROOT_DIR}/.venv/bin/python"
  fi

  # Run lightweight validation (no vLLM imports)
  if ! "${python_cmd}" - <<VALIDATE_SCRIPT
import sys
import os

# Minimal imports - just the models module, avoid importing anything that imports vLLM
sys.path.insert(0, "${ROOT_DIR}")

from src.config.models import (
    ALLOWED_TOOL_MODELS,
)
from src.helpers.models import get_allowed_chat_models
from src.helpers.quantization import (
    classify_prequantized_model,
    classify_trt_prequantized_model,
    is_awq_model_name,
)

deploy_mode = "${deploy_mode}"
chat_model = "${chat_model}" or None
tool_model = "${tool_model}" or None
quantization = "${quantization}" or None
chat_quant = "${chat_quant}" or None
engine = "${engine}".lower() or "trt"
if engine not in ("trt", "vllm"):
    engine = "trt"

errors = []

deploy_chat = deploy_mode in ("both", "chat")
deploy_tool = deploy_mode in ("both", "tool")
allowed_chat_models = get_allowed_chat_models(engine)

if deploy_chat:
    if not chat_model:
        errors.append("CHAT_MODEL is required when DEPLOY_MODE='both' or 'chat'")
    else:
        chat_allowlisted = os.path.exists(chat_model) or chat_model in allowed_chat_models
        if not chat_allowlisted:
            detected = classify_trt_prequantized_model(chat_model) or classify_prequantized_model(chat_model)
            suffix = f" (detected pre-quantized '{detected}')" if detected else ""
            errors.append(
                f"CHAT_MODEL must be allowlisted for engine '{engine}' or a local path{suffix}: {chat_model}"
            )

if deploy_tool:
    if not tool_model:
        errors.append("TOOL_MODEL is required when DEPLOY_MODE='both' or 'tool'")
    elif tool_model not in ALLOWED_TOOL_MODELS and not os.path.exists(tool_model):
        errors.append(
            f"TOOL_MODEL must be one of classifier models {ALLOWED_TOOL_MODELS}, got: {tool_model}"
        )

# AWQ + GPTQ check
if quantization == "awq" and deploy_chat and chat_model:
    if "GPTQ" in chat_model and not is_awq_model_name(chat_model):
        errors.append(
            f"For QUANTIZATION=awq, CHAT_MODEL must be a non-GPTQ (float) model. "
            f"Got: {chat_model}. Use a pre-quantized AWQ model or a float model instead."
        )

if errors:
    for err in errors:
        print(f"[validate] Model validation failed: {err}", file=sys.stderr)
    sys.exit(1)

print("[validate] Model validation passed")
sys.exit(0)
VALIDATE_SCRIPT
  then
    log_err "[validate] ✗ Model validation failed - check model names and allowlists"
    return 1
  fi
  return 0
}
