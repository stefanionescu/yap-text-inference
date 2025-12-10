#!/usr/bin/env bash

# Early model validation before deployment starts
# Calls Python to check models against allowlists without loading heavy vLLM deps

validate_models_early() {
  local deploy_mode="${DEPLOY_MODELS:-both}"
  local chat_model="${CHAT_MODEL:-}"
  local tool_model="${TOOL_MODEL:-}"
  local quantization="${QUANTIZATION:-}"
  local chat_quant="${CHAT_QUANTIZATION:-}"

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
    ALLOWED_CHAT_MODELS,
    ALLOWED_CLASSIFIER_MODELS,
    is_valid_model,
)
from src.config.quantization import classify_prequantized_model, is_awq_model_name

deploy_mode = "${deploy_mode}"
chat_model = "${chat_model}" or None
tool_model = "${tool_model}" or None
quantization = "${quantization}" or None
chat_quant = "${chat_quant}" or None

errors = []

def allow_prequantized_override(model, model_type):
    if model_type != "chat":
        return False
    quant = (chat_quant or quantization or "").lower()
    if not model or not quant:
        return False
    kind = classify_prequantized_model(model)
    if not kind:
        return False
    if quant == "awq" and kind != "awq":
        return False
    if quant.startswith("gptq") and kind != "gptq":
        return False
    if kind not in {"awq", "gptq"}:
        return False
    print(f"[WARNING] Using pre-quantized {kind.upper()} {model_type} model not in approved list: {model}")
    return True

deploy_chat = deploy_mode in ("both", "chat")
deploy_tool = deploy_mode in ("both", "tool")

if deploy_chat:
    if not chat_model:
        errors.append("CHAT_MODEL is required when DEPLOY_MODELS='both' or 'chat'")
    elif not is_valid_model(chat_model, ALLOWED_CHAT_MODELS, "chat"):
        if not allow_prequantized_override(chat_model, "chat"):
            errors.append(f"CHAT_MODEL must be one of allowed models, got: {chat_model}")

if deploy_tool:
    if not tool_model:
        errors.append("TOOL_MODEL is required when DEPLOY_MODELS='both' or 'tool'")
    elif tool_model not in ALLOWED_CLASSIFIER_MODELS and not os.path.exists(tool_model):
        errors.append(
            f"TOOL_MODEL must be one of classifier models {ALLOWED_CLASSIFIER_MODELS}, got: {tool_model}"
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
        print(f"[ERR ] Model validation failed: {err}", file=sys.stderr)
    sys.exit(1)

print("[INFO] Model validation passed")
sys.exit(0)
VALIDATE_SCRIPT
  then
    log_err "Model validation failed - check model names and allowlists"
    return 1
  fi
  return 0
}
