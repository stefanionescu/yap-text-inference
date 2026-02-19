#!/usr/bin/env python3
"""Strict model validation for Docker builds.

Validation rules are intentionally aligned with local script validation:
- Chat model: allowlisted for the selected engine OR explicit local path.
- Tool model: allowlisted OR explicit local path.
- TRT engine repo/label validation for TRT chat deployments.
"""

from __future__ import annotations

import os
import re
import sys


def _load_validation_config(engine: str | None = None) -> tuple[list[str], list[str]]:
    """Load allowlists from src config/helpers.

    Returns:
        (allowed_tool_models, allowed_chat_models_for_engine)
    """
    root_dir = os.environ.get("ROOT_DIR", "/app")
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    try:
        from src.config.models import ALLOWED_TOOL_MODELS  # noqa: PLC0415
        from src.helpers.models import get_allowed_chat_models  # noqa: PLC0415
    except Exception as exc:
        raise RuntimeError(f"failed to import validation config from src/: {exc}") from exc

    allowed_chat_models: list[str] = []
    if engine:
        allowed_chat_models = list(get_allowed_chat_models(engine))
    return list(ALLOWED_TOOL_MODELS), allowed_chat_models


def _is_local_path(value: str) -> bool:
    return bool(value and os.path.exists(value))


def validate_chat_model(model: str, engine: str, allowed_chat_models: list[str]) -> tuple[bool, str]:
    """Validate chat model configuration."""
    if not model:
        return False, "CHAT_MODEL is required but not set"

    if _is_local_path(model):
        return True, f"✓ CHAT_MODEL: local path ({model})"

    if "/" not in model:
        return False, f"CHAT_MODEL '{model}' is not a valid HuggingFace repo format (owner/repo)"

    if model not in allowed_chat_models:
        return False, (
            f"CHAT_MODEL '{model}' is not allowlisted for engine '{engine}'. "
            "Use an allowlisted model or a local model path."
        )

    return True, f"✓ CHAT_MODEL: {model}"


def validate_tool_model(model: str, allowed_tool_models: list[str]) -> tuple[bool, str]:
    """Validate tool model configuration."""
    if not model:
        return False, "TOOL_MODEL is required but not set"

    if _is_local_path(model):
        return True, f"✓ TOOL_MODEL: local path ({model})"

    if "/" not in model:
        return False, f"TOOL_MODEL '{model}' is not a valid HuggingFace repo format (owner/repo)"

    if model not in allowed_tool_models:
        return False, (
            f"TOOL_MODEL '{model}' is not in the allowed list. Use an allowlisted tool model or a local model path."
        )

    return True, f"✓ TOOL_MODEL: {model}"


def validate_trt_engine_repo(repo: str) -> tuple[bool, str]:
    """Validate TRT engine repo configuration."""
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
    engine: str,
    trt_engine_repo: str = "",
    trt_engine_label: str = "",
) -> tuple[bool, list[str]]:
    """Validate all models for a deploy mode."""
    deploy_chat = deploy_mode in ("chat", "both")
    deploy_tool = deploy_mode in ("tool", "both")
    normalized_engine = (engine or "").strip().lower()

    if deploy_chat and normalized_engine not in {"trt", "vllm"}:
        return False, [f"[validate] ✗ ENGINE must be 'trt' or 'vllm' for deploy mode '{deploy_mode}'"]

    try:
        allowed_tool_models, allowed_chat_models = _load_validation_config(normalized_engine if deploy_chat else None)
    except RuntimeError as exc:
        return False, [f"[validate] ✗ {exc}"]

    messages: list[str] = []
    all_valid = True

    if deploy_chat:
        valid, msg = validate_chat_model(chat_model, normalized_engine, allowed_chat_models)
        messages.append(f"[validate] {msg}")
        if not valid:
            all_valid = False

        if normalized_engine == "trt":
            valid, msg = validate_trt_engine_repo(trt_engine_repo)
            messages.append(f"[validate] {msg}")
            if not valid:
                all_valid = False

            valid, msg = validate_trt_engine_label(trt_engine_label)
            messages.append(f"[validate] {msg}")
            if not valid:
                all_valid = False

    if deploy_tool:
        valid, msg = validate_tool_model(tool_model, allowed_tool_models)
        messages.append(f"[validate] {msg}")
        if not valid:
            all_valid = False

    if deploy_mode not in ("chat", "tool", "both"):
        messages.append(f"[validate] Invalid DEPLOY_MODE: '{deploy_mode}'. Must be chat|tool|both")
        all_valid = False

    return all_valid, messages


def main() -> None:
    deploy_mode = os.environ.get("DEPLOY_MODE", "both")
    chat_model = os.environ.get("CHAT_MODEL", "")
    tool_model = os.environ.get("TOOL_MODEL", "")
    engine = os.environ.get("ENGINE", "").strip().lower()
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
