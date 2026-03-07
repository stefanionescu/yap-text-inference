"""Resolver functions for config-time computations.

These functions compute derived configuration values from environment
variables. They are called at module level in config/ modules but live
here because config/ must remain purely declarative (no ``def`` statements).
"""

from __future__ import annotations

import os
import json
from typing import TypedDict
from collections.abc import Mapping


class LimitValues(TypedDict):
    """Resolved limit values with concrete types."""

    CHAT_PROMPT_MAX_TOKENS: int
    CHAT_HISTORY_MAX_TOKENS: int
    USER_UTT_MAX_TOKENS: int
    HISTORY_RETENTION_PCT: int
    CONTEXT_BUFFER: int
    CHAT_MAX_LEN: int
    TRIMMED_HISTORY_LENGTH: int
    STREAM_FLUSH_MS: float
    CHAT_MAX_OUT: int
    WS_MESSAGE_WINDOW_SECONDS: float
    WS_MAX_MESSAGES_PER_WINDOW: int
    WS_CANCEL_WINDOW_SECONDS: float
    WS_MAX_CANCELS_PER_WINDOW: int
    MAX_CONCURRENT_CONNECTIONS: int | None


def _resolve_env_value(
    key: str,
    default: str,
    *,
    env: Mapping[str, str] | None,
) -> str:
    raw = os.getenv(key) if env is None else env.get(key)
    return default if raw is None else raw


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


def resolve_limit_values(*, env: Mapping[str, str] | None = None) -> LimitValues:
    """Resolve limits config values from an env mapping (or process env)."""
    chat_prompt_max_tokens = int(_resolve_env_value("CHAT_PROMPT_MAX_TOKENS", "1500", env=env))
    chat_history_max_tokens = int(_resolve_env_value("CHAT_HISTORY_MAX_TOKENS", "3000", env=env))
    user_utt_max_tokens = int(_resolve_env_value("USER_UTT_MAX_TOKENS", "500", env=env))
    history_retention_pct = int(_resolve_env_value("HISTORY_RETENTION_PCT", "66", env=env))
    context_buffer = int(_resolve_env_value("CONTEXT_BUFFER", "25", env=env))

    chat_max_len = chat_prompt_max_tokens + chat_history_max_tokens + user_utt_max_tokens + context_buffer
    trimmed_history_length = chat_history_max_tokens * history_retention_pct // 100

    stream_flush_ms = float(_resolve_env_value("STREAM_FLUSH_MS", "0", env=env))
    chat_max_out = int(_resolve_env_value("CHAT_MAX_OUT", "150", env=env))

    ws_message_window_seconds = float(_resolve_env_value("WS_MESSAGE_WINDOW_SECONDS", "60", env=env))
    ws_max_messages_per_window = int(_resolve_env_value("WS_MAX_MESSAGES_PER_WINDOW", "25", env=env))
    ws_cancel_window_seconds = float(
        _resolve_env_value("WS_CANCEL_WINDOW_SECONDS", str(ws_message_window_seconds), env=env)
    )
    ws_max_cancels_per_window = int(
        _resolve_env_value("WS_MAX_CANCELS_PER_WINDOW", str(ws_max_messages_per_window), env=env)
    )

    max_concurrent_raw = _resolve_env_value("MAX_CONCURRENT_CONNECTIONS", "", env=env)
    max_concurrent_connections: int | None = int(max_concurrent_raw) if max_concurrent_raw else None

    return {
        "CHAT_PROMPT_MAX_TOKENS": chat_prompt_max_tokens,
        "CHAT_HISTORY_MAX_TOKENS": chat_history_max_tokens,
        "USER_UTT_MAX_TOKENS": user_utt_max_tokens,
        "HISTORY_RETENTION_PCT": history_retention_pct,
        "CONTEXT_BUFFER": context_buffer,
        "CHAT_MAX_LEN": chat_max_len,
        "TRIMMED_HISTORY_LENGTH": trimmed_history_length,
        "STREAM_FLUSH_MS": stream_flush_ms,
        "CHAT_MAX_OUT": chat_max_out,
        "WS_MESSAGE_WINDOW_SECONDS": ws_message_window_seconds,
        "WS_MAX_MESSAGES_PER_WINDOW": ws_max_messages_per_window,
        "WS_CANCEL_WINDOW_SECONDS": ws_cancel_window_seconds,
        "WS_MAX_CANCELS_PER_WINDOW": ws_max_cancels_per_window,
        "MAX_CONCURRENT_CONNECTIONS": max_concurrent_connections,
    }


__all__ = [
    "LimitValues",
    "resolve_gpu_fracs",
    "resolve_batch_scale_gpu_frac_cap",
    "load_logit_bias_from_file",
    "resolve_limit_values",
]
