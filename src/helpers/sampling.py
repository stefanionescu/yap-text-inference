"""Sampling configuration helpers."""

import os


def build_logit_bias_map(default_map: dict[str, float]) -> dict[str, float]:
    """Build logit bias map from file or return default.
    
    If CHAT_LOGIT_BIAS_FILE env var is set, loads the JSON file and returns
    its contents. Falls back to default_map on any error.
    
    Args:
        default_map: Default logit bias mapping to use if file not specified or invalid.
        
    Returns:
        Logit bias map (token string -> bias value).
    """
    env_path = os.getenv("CHAT_LOGIT_BIAS_FILE")
    if not env_path:
        return default_map
    try:
        import json
        with open(env_path, encoding="utf-8") as infile:
            loaded = json.load(infile)
        if not isinstance(loaded, dict):
            raise ValueError("CHAT_LOGIT_BIAS_FILE must contain a JSON object")
        cleaned: dict[str, float] = {}
        for key, value in loaded.items():
            if not isinstance(key, str):
                continue
            try:
                cleaned[key] = float(value)
            except (TypeError, ValueError):
                continue
        return cleaned or default_map
    except Exception:
        return default_map


__all__ = [
    "build_logit_bias_map",
]

