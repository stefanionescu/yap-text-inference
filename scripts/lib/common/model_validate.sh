#!/usr/bin/env bash

# Early model validation before deployment starts
# Calls Python to check models against allowlists without loading heavy vLLM deps

validate_models_early() {
  local deploy_mode="${DEPLOY_MODELS:-both}"
  local chat_model="${CHAT_MODEL:-}"
  local tool_model="${TOOL_MODEL:-}"
  local dual_model="${DUAL_MODEL:-}"
  local quantization="${QUANTIZATION:-}"
  local chat_quant="${CHAT_QUANTIZATION:-}"
  local tool_quant="${TOOL_QUANTIZATION:-}"

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
    ALLOWED_TOOL_MODELS,
    ALLOWED_DUAL_MODELS,
    is_valid_model,
)
from src.config.quantization import classify_prequantized_model, is_awq_model_name

deploy_mode = "${deploy_mode}"
chat_model = "${chat_model}" or None
tool_model = "${tool_model}" or None
dual_model = "${dual_model}" or None
quantization = "${quantization}" or None
chat_quant = "${chat_quant}" or None
tool_quant = "${tool_quant}" or None

errors = []

def effective_quantization(model_type):
    if model_type == "chat":
        return (chat_quant or quantization or "").lower()
    tq = (tool_quant or "").lower()
    if tq:
        return tq
    return (quantization or "").lower()

def allow_prequantized_override(model, model_type):
    quant = effective_quantization(model_type)
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

deploy_dual = deploy_mode == "dual"
deploy_chat = deploy_mode in ("both", "chat", "dual")
deploy_tool = deploy_mode in ("both", "tool", "dual")

if deploy_dual:
    if not dual_model:
        errors.append("DUAL_MODEL is required when DEPLOY_MODELS='dual'")
    elif not is_valid_model(dual_model, ALLOWED_DUAL_MODELS, "dual"):
        if not allow_prequantized_override(dual_model, "chat"):
            errors.append(f"DUAL_MODEL must be one of: {ALLOWED_DUAL_MODELS}, got: {dual_model}")
else:
    if deploy_chat:
        if not chat_model:
            errors.append("CHAT_MODEL is required when DEPLOY_MODELS='both' or 'chat'")
        elif not is_valid_model(chat_model, ALLOWED_CHAT_MODELS, "chat"):
            if not allow_prequantized_override(chat_model, "chat"):
                errors.append(f"CHAT_MODEL must be one of allowed models, got: {chat_model}")
    
    if deploy_tool:
        if not tool_model:
            errors.append("TOOL_MODEL is required when DEPLOY_MODELS='both' or 'tool'")
        elif not is_valid_model(tool_model, ALLOWED_TOOL_MODELS, "tool"):
            if not allow_prequantized_override(tool_model, "tool"):
                errors.append(f"TOOL_MODEL must be one of allowed models, got: {tool_model}")

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
