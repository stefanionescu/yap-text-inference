#!/usr/bin/env python3
"""Model validation for Docker builds.

Sources validation rules from src/config to ensure Docker and Python stay in sync.
This module is called by build scripts to validate model configurations.
"""

import os
import re
import sys


def get_allowed_tool_models() -> list[str]:
    """Get the allowed tool models from Python config."""
    # Add src to path for imports
    root_dir = os.environ.get("ROOT_DIR", "/app")
    sys.path.insert(0, root_dir)

    try:
        from src.config.models import ALLOWED_TOOL_MODELS  # noqa: PLC0415

        return list(ALLOWED_TOOL_MODELS)
    except ImportError:
        # Fallback for build-time when src is in build context
        return [
            "yapwithai/yap-longformer-screenshot-intent",
            "yapwithai/yap-modernbert-screenshot-intent",
        ]


def get_awq_model_markers() -> list[str]:
    """Get the AWQ model markers from Python config."""
    root_dir = os.environ.get("ROOT_DIR", "/app")
    sys.path.insert(0, root_dir)

    try:
        from src.config.quantization import AWQ_MODEL_MARKERS  # noqa: PLC0415

        return list(AWQ_MODEL_MARKERS)
    except ImportError:
        # Fallback for build-time
        return ["awq", "w4a16", "compressed-tensors", "autoround"]


def is_prequantized_model(model: str) -> bool:
    """Check if model name indicates pre-quantization."""
    if not model or "/" not in model:
        return False

    model_lower = model.lower()
    markers = get_awq_model_markers()

    # Also check for gptq
    all_markers = markers + ["gptq"]

    return any(marker in model_lower for marker in all_markers)


def classify_quantization(model: str) -> str:
    """Classify the quantization type of a model."""
    if not model:
        return ""

    model_lower = model.lower()
    markers = get_awq_model_markers()

    # AWQ and related (W4A16, compressed-tensors, autoround all use awq_marlin)
    if any(marker in model_lower for marker in markers):
        return "awq"

    # GPTQ
    if "gptq" in model_lower:
        return "gptq"

    return ""


def validate_chat_model(model: str, engine: str = "vllm") -> tuple[bool, str]:
    """Validate chat model configuration.

    Args:
        model: HuggingFace model repo ID
        engine: "vllm" or "trt"

    Returns:
        (is_valid, message) tuple
    """
    if not model:
        return False, "CHAT_MODEL is required but not set"

    if "/" not in model:
        return False, f"CHAT_MODEL '{model}' is not a valid HuggingFace repo format (owner/repo)"

    if engine == "vllm":
        if not is_prequantized_model(model):
            markers = get_awq_model_markers() + ["gptq"]
            return False, (
                f"CHAT_MODEL '{model}' is not a pre-quantized model. "
                f"Chat model name must contain one of: {', '.join(markers)}"
            )

        quant_type = classify_quantization(model)
        return True, f"✓ CHAT_MODEL: {model} ({quant_type})"

    # TRT just needs valid HF repo
    return True, f"✓ CHAT_MODEL: {model}"


def validate_tool_model(model: str) -> tuple[bool, str]:
    """Validate tool model configuration.

    Returns:
        (is_valid, message) tuple
    """
    if not model:
        return False, "TOOL_MODEL is required but not set"

    allowed = get_allowed_tool_models()
    if model in allowed:
        return True, f"✓ TOOL_MODEL: {model}"

    return False, (f"TOOL_MODEL '{model}' is not in the allowed list. Allowed: {', '.join(allowed)}")


def validate_trt_engine_repo(repo: str) -> tuple[bool, str]:
    """Validate TRT engine repo configuration.

    Note: TRT_ENGINE_REPO defaults to CHAT_MODEL in the build script, so this
    validation only fails if neither is set.
    """
    if not repo:
        return False, (
            "✗ TRT_ENGINE_REPO is not set and CHAT_MODEL is empty. "
            "Set CHAT_MODEL (TRT_ENGINE_REPO defaults to it) or set TRT_ENGINE_REPO explicitly."
        )

    if "/" not in repo:
        return False, f"TRT_ENGINE_REPO '{repo}' is not a valid HuggingFace repo format (owner/repo)"

    return True, f"✓ TRT_ENGINE_REPO: {repo}"


def validate_trt_engine_label(label: str) -> tuple[bool, str]:
    """Validate TRT engine label format."""
    if not label:
        return False, (
            "✗ TRT_ENGINE_LABEL is REQUIRED. "
            "Format: sm{arch}_trt-llm-{version}_cuda{version}. "
            "Example: TRT_ENGINE_LABEL=sm90_trt-llm-0.17.0_cuda12.8"
        )

    # Pattern: sm{digits}_trt-llm-{version}_cuda{version}
    pattern = r"^sm\d+_trt-llm-[\d.]+.*_cuda[\d.]+$"
    if not re.match(pattern, label):
        return False, (
            f"✗ TRT_ENGINE_LABEL '{label}' has invalid format. Expected: sm{{arch}}_trt-llm-{{version}}_cuda{{version}}"
        )

    return True, f"✓ TRT_ENGINE_LABEL: {label}"


def validate_for_deploy(
    deploy_mode: str,
    chat_model: str,
    tool_model: str,
    engine: str = "vllm",
    trt_engine_repo: str = "",
    trt_engine_label: str = "",
) -> tuple[bool, list[str]]:
    """Validate all models for a deploy mode.

    Returns:
        (all_valid, messages) tuple
    """
    messages = []
    all_valid = True

    if deploy_mode in ("chat", "both"):
        valid, msg = validate_chat_model(chat_model, engine)
        messages.append(f"[validate] {msg}")
        if not valid:
            all_valid = False

        if engine == "trt":
            valid, msg = validate_trt_engine_repo(trt_engine_repo)
            messages.append(f"[validate] {msg}")
            if not valid:
                all_valid = False

            valid, msg = validate_trt_engine_label(trt_engine_label)
            messages.append(f"[validate] {msg}")
            if not valid:
                all_valid = False

    if deploy_mode in ("tool", "both"):
        valid, msg = validate_tool_model(tool_model)
        messages.append(f"[validate] {msg}")
        if not valid:
            all_valid = False

    if deploy_mode not in ("chat", "tool", "both"):
        messages.append(f"[validate] Invalid DEPLOY_MODE: '{deploy_mode}'. Must be chat|tool|both")
        all_valid = False

    return all_valid, messages


def main() -> None:
    """CLI interface for validation."""
    deploy_mode = os.environ.get("DEPLOY_MODE", "both")
    chat_model = os.environ.get("CHAT_MODEL", "")
    tool_model = os.environ.get("TOOL_MODEL", "")
    engine = os.environ.get("ENGINE", "vllm")
    trt_engine_repo = os.environ.get("TRT_ENGINE_REPO", "")
    trt_engine_label = os.environ.get("TRT_ENGINE_LABEL", "")

    all_valid, messages = validate_for_deploy(
        deploy_mode,
        chat_model,
        tool_model,
        engine,
        trt_engine_repo,
        trt_engine_label,
    )

    for msg in messages:
        print(msg)

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
