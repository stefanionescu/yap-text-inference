from .tokenizer_utils import exact_token_count, trim_text_to_token_limit_exact


def approx_token_count(text: str) -> int:
    # For backwards compatibility: remains exact now
    return exact_token_count(text)


def trim_text_to_token_limit(text: str, max_tokens: int, keep: str = "end") -> str:
    return trim_text_to_token_limit_exact(text, max_tokens=max_tokens, keep=keep)


