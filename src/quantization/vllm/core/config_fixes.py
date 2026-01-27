"""Post-quantization config.json fixes for model family compatibility."""

from __future__ import annotations

import os
import json
from typing import Any

from src.helpers.model_profiles import get_model_profile


def apply_post_quantization_fixes(
    output_dir: str,
    model_path: str,
) -> bool:
    """Apply model-family-specific config.json fixes after quantization.

    Some model families require specific config values to work with vLLM or other
    inference engines. This function looks up the model profile and applies any
    necessary overrides to the exported config.json.

    Args:
        output_dir: Directory containing the quantized model artifacts.
        model_path: Original model path/identifier (used for profile matching).

    Returns:
        True if fixes were applied (or none needed), False on error.
    """
    profile = get_model_profile(model_path)
    if profile is None or not profile.config_overrides:
        return True  # No fixes needed

    config_path = os.path.join(output_dir, "config.json")
    if not os.path.isfile(config_path):
        print(f"[awq] Warning: config.json not found at {config_path}, skipping fixes")
        return True

    try:
        with open(config_path, encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Warning: failed to read config.json for fixes: {exc}")
        return False

    applied_fixes: list[str] = []
    for key, value in profile.config_overrides.items():
        old_value = config.get(key)
        if old_value != value:
            config[key] = value
            applied_fixes.append(f"{key}: {old_value!r} -> {value!r}")

    if not applied_fixes:
        return True  # Config already correct

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Trailing newline for cleaner diffs
    except Exception as exc:  # noqa: BLE001
        print(f"[awq] Warning: failed to write config.json fixes: {exc}")
        return False

    print(f"[awq] Applied {profile.name} config fixes: {', '.join(applied_fixes)}")
    return True

