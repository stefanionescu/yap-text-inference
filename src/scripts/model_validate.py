"""Early model validation before deployment starts.

Lightweight validation that checks models against allowlists without
loading heavy vLLM dependencies. Called from shell scripts to fail fast
before expensive operations.
"""

from __future__ import annotations

import os
import sys


def validate_models(
    deploy_mode: str,
    chat_model: str | None,
    tool_model: str | None,
    quantization: str | None,
    chat_quant: str | None,
    engine: str,
) -> list[str]:
    """Validate model configuration against allowlists.

    Args:
        deploy_mode: Deployment mode (both, chat, tool).
        chat_model: Chat model identifier or path.
        tool_model: Tool model identifier or path.
        quantization: Base quantization setting.
        chat_quant: Chat-specific quantization override.
        engine: Inference engine (trt, vllm).

    Returns:
        List of error messages. Empty list means validation passed.
    """
    from src.config.models import ALLOWED_TOOL_MODELS
    from src.helpers.models import get_allowed_chat_models
    from src.helpers.quantization import (
        classify_prequantized_model,
        classify_trt_prequantized_model,
        is_awq_model_name,
    )

    errors: list[str] = []

    # Normalize engine
    engine = (engine or "trt").lower()
    if engine not in ("trt", "vllm"):
        engine = "trt"

    deploy_chat = deploy_mode in ("both", "chat")
    deploy_tool = deploy_mode in ("both", "tool")
    allowed_chat_models = get_allowed_chat_models(engine)

    if deploy_chat:
        if not chat_model:
            errors.append("CHAT_MODEL is required when DEPLOY_MODE='both' or 'chat'")
        else:
            chat_allowlisted = (
                os.path.exists(chat_model) or chat_model in allowed_chat_models
            )
            if not chat_allowlisted:
                detected = classify_trt_prequantized_model(
                    chat_model
                ) or classify_prequantized_model(chat_model)
                suffix = f" (detected pre-quantized '{detected}')" if detected else ""
                errors.append(
                    f"CHAT_MODEL must be allowlisted for engine '{engine}' "
                    f"or a local path{suffix}: {chat_model}"
                )

    if deploy_tool:
        if not tool_model:
            errors.append("TOOL_MODEL is required when DEPLOY_MODE='both' or 'tool'")
        elif tool_model not in ALLOWED_TOOL_MODELS and not os.path.exists(tool_model):
            errors.append(
                f"TOOL_MODEL must be one of classifier models "
                f"{ALLOWED_TOOL_MODELS}, got: {tool_model}"
            )

    # AWQ + GPTQ check
    if quantization == "awq" and deploy_chat and chat_model:
        if "GPTQ" in chat_model and not is_awq_model_name(chat_model):
            errors.append(
                f"For QUANTIZATION=awq, CHAT_MODEL must be a non-GPTQ (float) model. "
                f"Got: {chat_model}. Use a pre-quantized AWQ model or a float model instead."
            )

    return errors


if __name__ == "__main__":
    # CLI interface for shell scripts
    # Reads configuration from environment variables
    deploy_mode = os.environ.get("DEPLOY_MODE", "both")
    chat_model = os.environ.get("CHAT_MODEL") or None
    tool_model = os.environ.get("TOOL_MODEL") or None
    quantization = os.environ.get("QUANTIZATION") or None
    chat_quant = os.environ.get("CHAT_QUANTIZATION") or None
    engine = os.environ.get("INFERENCE_ENGINE") or os.environ.get("ENGINE_TYPE", "trt")

    errors = validate_models(
        deploy_mode=deploy_mode,
        chat_model=chat_model,
        tool_model=tool_model,
        quantization=quantization,
        chat_quant=chat_quant,
        engine=engine,
    )

    if errors:
        for err in errors:
            print(f"[validate] ✗ {err}", file=sys.stderr)
        sys.exit(1)

    # Print separate success messages for each validated model type
    deploy_chat = deploy_mode in ("both", "chat")
    deploy_tool = deploy_mode in ("both", "tool")
    
    if deploy_chat:
        print("[validate] ✓ Chat model validation passed")
    if deploy_tool:
        print("[validate] ✓ Tool model validation passed")
    
    sys.exit(0)

