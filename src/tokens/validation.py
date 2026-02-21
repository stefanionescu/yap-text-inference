"""Tokenizer validation for model directories.

This module provides validation to ensure tokenizers exist locally
before the server starts. This prevents runtime failures and ensures
we never silently fall back to fetching tokenizers from HuggingFace.

Validation checks for:
1. tokenizer.json (fast tokenizers library format)
2. tokenizer_config.json (transformers AutoTokenizer format)

At least one of these must exist for local model directories.
HuggingFace repo IDs are validated at tokenizer load time instead.
"""

from __future__ import annotations

import os
from ..config.deploy import HF_REPO_PATTERN
from src.state import TokenizerValidationResult


def _invalid_result(model_path: str, error_message: str) -> TokenizerValidationResult:
    return TokenizerValidationResult(
        valid=False,
        error_message=error_message,
        model_path=model_path,
        has_tokenizer_json=False,
        has_tokenizer_config=False,
    )


def _remote_result(model_path: str) -> TokenizerValidationResult:
    return TokenizerValidationResult(
        valid=True,
        error_message=None,
        model_path=model_path,
        has_tokenizer_json=False,
        has_tokenizer_config=False,
        is_remote=True,
    )


def _missing_tokenizer_message(model_path: str, tokenizer_json: str, tokenizer_config: str) -> str:
    return (
        f"Tokenizer files not found in model directory: {model_path}\n"
        "Expected at least one of:\n"
        f"  - {tokenizer_json}\n"
        f"  - {tokenizer_config}\n"
        "\n"
        "If using a pre-quantized model from HuggingFace:\n"
        "  Ensure the download completed successfully and includes tokenizer files.\n"
        "\n"
        "If using a locally quantized model:\n"
        "  Re-run quantization to regenerate the tokenizer files."
    )


def _is_huggingface_repo_id(path: str) -> bool:
    """Check if a path looks like a HuggingFace repo ID.

    HuggingFace repo IDs have the format: org/model-name or user/model-name
    This is distinct from local paths which typically start with / or ./
    """
    if not path:
        return False
    # If it exists locally, it's not a remote repo ID
    if os.path.exists(path):
        return False
    # Check if it matches the HF repo ID pattern
    return bool(HF_REPO_PATTERN.match(path))


def validate_tokenizer_exists(model_path: str) -> TokenizerValidationResult:
    """Validate that a tokenizer exists locally for the given model.

    For local directories: Checks for tokenizer.json or tokenizer_config.json.
    For HuggingFace repo IDs: Skips validation (tokenizer fetched at load time).

    Args:
        model_path: Local directory path or HuggingFace repo ID.

    Returns:
        TokenizerValidationResult with validation status and details.
    """
    if not model_path:
        return _invalid_result(model_path, "Model path is empty")

    # HuggingFace repo IDs are validated at load time, not here
    if _is_huggingface_repo_id(model_path):
        return _remote_result(model_path)

    if not os.path.isdir(model_path):
        return _invalid_result(
            model_path,
            (
                f"Model directory does not exist: {model_path}\n"
                "Ensure the model has been downloaded or the path is correct."
            ),
        )

    tokenizer_json = os.path.join(model_path, "tokenizer.json")
    tokenizer_config = os.path.join(model_path, "tokenizer_config.json")

    has_tokenizer_json = os.path.isfile(tokenizer_json)
    has_tokenizer_config = os.path.isfile(tokenizer_config)

    if has_tokenizer_json or has_tokenizer_config:
        return TokenizerValidationResult(
            valid=True,
            error_message=None,
            model_path=model_path,
            has_tokenizer_json=has_tokenizer_json,
            has_tokenizer_config=has_tokenizer_config,
        )

    return _invalid_result(
        model_path,
        _missing_tokenizer_message(model_path, tokenizer_json, tokenizer_config),
    )


def validate_model_tokenizer(
    model_path: str | None,
    model_name: str,
    deploy_enabled: bool,
) -> str | None:
    """Validate tokenizer for a model if deployment is enabled.

    This is a convenience wrapper for startup validation. Returns an
    error message if validation fails, None if successful or skipped.

    Args:
        model_path: Path to the model directory (may be None if not configured).
        model_name: Human-readable name for error messages (e.g., "CHAT_MODEL").
        deploy_enabled: Whether this model is configured for deployment.

    Returns:
        Error message string if validation failed, None otherwise.
    """
    if not deploy_enabled:
        return None

    if not model_path:
        # Model path validation is handled elsewhere (validate_env checks this)
        return None

    result = validate_tokenizer_exists(model_path)
    if result.valid:
        return None

    return f"{model_name} tokenizer validation failed:\n{result.error_message}"


__all__ = [
    "validate_tokenizer_exists",
    "validate_model_tokenizer",
]
