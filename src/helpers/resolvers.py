"""Resolver functions for config-time computations.

These functions compute derived configuration values from environment
variables. They are called at module level in config/ modules but live
here because config/ must remain purely declarative (no ``def`` statements).
"""

from __future__ import annotations

import os
import json


def resolve_gpu_fracs(deploy_chat: bool, deploy_tool: bool) -> tuple[float, float]:
    """Resolve GPU memory fractions based on deployment mode.

    When both chat and tool are deployed, memory is partitioned conservatively.
    When only one component is deployed, it gets more memory.

    Args:
        deploy_chat: Whether chat engine is being deployed.
        deploy_tool: Whether tool model is being deployed.

    Returns:
        Tuple of (chat_gpu_frac, tool_gpu_frac).
    """
    if deploy_chat and deploy_tool:
        chat_frac = float(os.getenv("CHAT_GPU_FRAC", "0.70"))
        tool_frac = float(os.getenv("TOOL_GPU_FRAC", "0.20"))
    else:
        chat_frac = float(os.getenv("CHAT_GPU_FRAC", "0.90"))
        tool_frac = float(os.getenv("TOOL_GPU_FRAC", "0.90"))
    return chat_frac, tool_frac


def resolve_batch_scale_gpu_frac_cap(deploy_chat: bool, deploy_tool: bool) -> float:
    """Resolve GPU fraction cap for batch scaling.

    Prevents pushing memory allocation beyond the configured GPU fraction.
    Uses explicit env var if set, otherwise derives from CHAT_GPU_FRAC.

    Args:
        deploy_chat: Whether chat engine is being deployed.
        deploy_tool: Whether tool model is being deployed.

    Returns:
        GPU fraction cap value.
    """
    env_cap = os.getenv("BATCH_SCALE_GPU_FRAC_CAP")
    if env_cap is not None:
        return float(env_cap)

    if deploy_chat and deploy_tool:
        return float(os.getenv("CHAT_GPU_FRAC", "0.70"))
    return float(os.getenv("CHAT_GPU_FRAC", "0.90"))


def load_logit_bias_from_file(
    file_path: str | None,
    default_map: dict[str, float],
) -> dict[str, float]:
    """Load logit bias map from JSON file or return default.

    If file_path is set, loads the JSON file and returns its contents.
    Falls back to default_map on any error.

    Args:
        file_path: Path to JSON file, or None to use default.
        default_map: Default logit bias mapping.

    Returns:
        Logit bias map (token string -> bias value).
    """
    if not file_path:
        return default_map
    try:
        with open(file_path, encoding="utf-8") as infile:
            loaded = json.load(infile)
        if not isinstance(loaded, dict):
            return default_map
        cleaned: dict[str, float] = {}
        for key, value in loaded.items():
            if isinstance(key, str):
                try:
                    cleaned[key] = float(value)
                except (TypeError, ValueError):
                    continue
        return cleaned or default_map
    except Exception:
        return default_map


__all__ = [
    "resolve_gpu_fracs",
    "resolve_batch_scale_gpu_frac_cap",
    "load_logit_bias_from_file",
]
