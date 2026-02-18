"""Early model validation before deployment starts.

Lightweight validation that checks models against allowlists without
loading heavy vLLM dependencies. Called from shell scripts to fail fast
before expensive operations.
"""

from __future__ import annotations

import os
import sys

VALIDATE_SUPPORTED_ENGINES: tuple[str, ...] = ("trt", "vllm")


def validate_models(
    deploy_mode: str,
    chat_model: str | None,
    tool_model: str | None,
    chat_quantization: str | None,
    engine: str,
) -> list[str]:
    """Validate model configuration against allowlists.

    Args:
        deploy_mode: Deployment mode (both, chat, tool).
        chat_model: Chat model identifier or path.
        tool_model: Tool model identifier or path.
        chat_quantization: Chat quantization (auto-detected from model name or config files).
        engine: Inference engine (trt, vllm).

    Returns:
        List of error messages. Empty list means validation passed.
    """
    from src.config.models import ALLOWED_TOOL_MODELS  # noqa: PLC0415
    from src.helpers.models import get_allowed_chat_models  # noqa: PLC0415
    from src.helpers.quantization import (  # noqa: PLC0415
        is_awq_model_name,
        classify_prequantized_model,
        classify_trt_prequantized_model,
    )

    errors: list[str] = []

    engine = (engine or "").lower()
    if engine not in VALIDATE_SUPPORTED_ENGINES:
        errors.append(f"INFERENCE_ENGINE must be one of {VALIDATE_SUPPORTED_ENGINES}, got: {engine}")
        return errors

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
            errors.append(f"TOOL_MODEL must be one of tool models {ALLOWED_TOOL_MODELS}, got: {tool_model}")

    # AWQ + GPTQ conflict check
    if (
        chat_quantization == "awq"
        and deploy_chat
        and chat_model
        and "GPTQ" in chat_model
        and not is_awq_model_name(chat_model)
    ):
        errors.append(
            f"CHAT_QUANTIZATION=awq but CHAT_MODEL appears to be GPTQ. "
            f"Got: {chat_model}. Use a pre-quantized AWQ model instead."
        )

    return errors


if __name__ == "__main__":
    # CLI interface for shell scripts
    # Reads configuration from environment variables
    deploy_mode = os.environ.get("DEPLOY_MODE") or ""
    chat_model = os.environ.get("CHAT_MODEL") or None
    tool_model = os.environ.get("TOOL_MODEL") or None
    chat_quantization = os.environ.get("CHAT_QUANTIZATION") or None
    engine = os.environ.get("INFERENCE_ENGINE") or ""

    if deploy_mode not in ("both", "chat", "tool"):
        print(
            "[validate] ✗ DEPLOY_MODE must be one of ('both', 'chat', 'tool') and must be exported by shell config.",
            file=sys.stderr,
        )
        sys.exit(1)

    errors = validate_models(
        deploy_mode=deploy_mode,
        chat_model=chat_model,
        tool_model=tool_model,
        chat_quantization=chat_quantization,
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
