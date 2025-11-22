"""Sampling defaults for chat and tool models.

All values may be overridden via environment variables when applicable.
Stop sequences are centralized here for consistency.
"""

import os


# --- Chat sampling ---
CHAT_TEMPERATURE = float(os.getenv("CHAT_TEMPERATURE", "1.0"))
CHAT_TOP_P = float(os.getenv("CHAT_TOP_P", "0.80"))
CHAT_TOP_K = int(os.getenv("CHAT_TOP_K", "40"))
CHAT_MIN_P = float(os.getenv("CHAT_MIN_P", "0.05"))
CHAT_REPEAT_PENALTY = float(os.getenv("CHAT_REPEAT_PENALTY", "1.05"))
CHAT_PRESENCE_PENALTY = float(os.getenv("CHAT_PRESENCE_PENALTY", "0.05"))
CHAT_FREQUENCY_PENALTY = float(os.getenv("CHAT_FREQUENCY_PENALTY", "0.05"))

# Extra STOP sequences used by chat model
CHAT_STOP = [
    " |",
    "  |",
    "<|im_end|>",
    "|im_end|>",
    "<|assistant|>",
    "<|user|>",
    " ‍♀️",
    " ‍♂️",
    "<|end|>",
    "</s>",
    "User ",
    "User:",
    "Assistant:",
    "\nUser",
    "\nAssistant",
    "[SYSTEM_PROMPT]",
    "[/SYSTEM_PROMPT]",
]


# --- Tool sampling ---
TOOL_TEMPERATURE = float(os.getenv("TOOL_TEMPERATURE", "0.05"))
TOOL_TOP_P = float(os.getenv("TOOL_TOP_P", "1.0"))
TOOL_TOP_K = int(os.getenv("TOOL_TOP_K", "1"))
TOOL_STOP = ["\n", "</s>"]


_DEFAULT_LOGIT_BIAS = {
    "*winks*": -100.0,
    "*winks*.": -100.0,
    " *winks*.": -100.0,
    "*smirks*": -100.0,
    "*giggles*": -100.0,
    "*purrs*": -100.0,
    "*blushes*": -100.0,
    ":)": -100.0,
    ";)": -100.0,
    " ;)": -100,
    " ;) ": -100,
    ":D": -100.0,
    ":(": -100.0,
    ":P": -100.0,
    "Oh honey": -100.0,
    "Oh, honey": -100.0,
    "Oh honey...": -100.0,
    "Well honey": -100.0,
    "Well honey,": -100.0,
    "Well, well": -100.0,
    "Well well": -100.0,
    "Well, well, well": -100.0,
    "Well, well!": -100.0,
    "what's really on your mind?": -100.0,
    "Now let's talk about": -100.0,
    "~": -100.0,
    " - ": -100,
}


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
    "CHAT_REPEAT_PENALTY",
    "CHAT_PRESENCE_PENALTY",
    "CHAT_FREQUENCY_PENALTY",
    "CHAT_STOP",
    "CHAT_LOGIT_BIAS",
    "TOOL_TEMPERATURE",
    "TOOL_TOP_P",
    "TOOL_TOP_K",
    "TOOL_STOP",
]


