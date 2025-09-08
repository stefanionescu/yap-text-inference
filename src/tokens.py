import os
import math


AVG_CHARS_PER_TOKEN = int(os.getenv("AVG_CHARS_PER_TOKEN", "4"))


def approx_token_count(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / max(1, AVG_CHARS_PER_TOKEN)))


def trim_text_to_token_limit(text: str, max_tokens: int, keep: str = "end") -> str:
    if max_tokens <= 0 or not text:
        return ""
    char_limit = max_tokens * max(1, AVG_CHARS_PER_TOKEN)
    if len(text) <= char_limit:
        return text
    if keep == "start":
        trimmed = text[:char_limit]
        # avoid cutting mid-word harshly
        last_space = trimmed.rfind(" ")
        return trimmed if last_space == -1 else trimmed[: last_space + 1]
    # keep == "end" (default)
    trimmed = text[-char_limit:]
    first_space = trimmed.find(" ")
    return trimmed if first_space == -1 else trimmed[first_space + 1 :]


