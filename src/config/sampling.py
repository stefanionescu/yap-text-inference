"""Sampling defaults for chat models.

All values may be overridden via environment variables when applicable.
Stop sequences are centralized here for consistency.
"""

import os


# --- Chat sampling ---
CHAT_TEMPERATURE = float(os.getenv("CHAT_TEMPERATURE", "0.8"))
CHAT_TOP_P = float(os.getenv("CHAT_TOP_P", "0.95"))
CHAT_TOP_K = int(os.getenv("CHAT_TOP_K", "30"))
CHAT_MIN_P = float(os.getenv("CHAT_MIN_P", "0"))
CHAT_REPETITION_PENALTY = float(os.getenv("CHAT_REPETITION_PENALTY", "1.0"))
CHAT_PRESENCE_PENALTY = float(os.getenv("CHAT_PRESENCE_PENALTY", "0"))
CHAT_FREQUENCY_PENALTY = float(os.getenv("CHAT_FREQUENCY_PENALTY", "0"))


# What words/text to discourage
_DEFAULT_LOGIT_BIAS = {
    "*": -100,
    "(": -100,
    ")": -100,
    "~": -100,
    " - ": -100,
    "-": -100,
    "Mmh": -100,
    "hmm": -100,
    "…": -100,
    "Damn": -100,
    "stud": -100,
}

# STOP sequences
INFERENCE_STOP = [
    # ChatML format
    "<|im_end|>",
    "|im_end|>",
    "<|assistant|>",
    "<|user|>",
    "<|end|>",
    # Gemma 1/2 format
    "<end_of_turn>",
    "<start_of_turn>",
    # Gemma 3 format
    "<|eot_id|>",
    "<|start_header_id|>",
    # Kimi / Kimi Linear format
    "<|im_user|>",
    "<|im_system|>",
    "[EOS]",
    "[EOT]",
    # DeepSeek V2/V3 format (uses fullwidth vertical bars)
    "<｜end▁of▁sentence｜>",
    "<｜begin▁of▁sentence｜>",
    "User:",  # DeepSeek uses "User:" prefix
    # General
    "[SYSTEM_PROMPT]",
    "[/SYSTEM_PROMPT]",
]


def _build_logit_bias_map(raw_map: dict[str, float]) -> dict[str, float]:
    env_path = os.getenv("CHAT_LOGIT_BIAS_FILE")
    if not env_path:
        return raw_map
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
        return cleaned or raw_map
    except Exception:
        return raw_map


CHAT_LOGIT_BIAS = _build_logit_bias_map(_DEFAULT_LOGIT_BIAS)


__all__ = [
    "CHAT_TEMPERATURE",
    "CHAT_TOP_P",
    "CHAT_TOP_K",
    "CHAT_MIN_P",
    "CHAT_REPETITION_PENALTY",
    "CHAT_PRESENCE_PENALTY",
    "CHAT_FREQUENCY_PENALTY",
    "INFERENCE_STOP",
    "CHAT_LOGIT_BIAS",
]

