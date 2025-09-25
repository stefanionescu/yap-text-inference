"""Token counting utilities with backwards compatibility."""

from .tokenizer_utils import exact_token_count, trim_text_to_token_limit_exact


def approx_token_count(text: str) -> int:
    """Approximate token count (now exact for backwards compatibility).
    
    Args:
        text: Input text to count tokens for
        
    Returns:
        Token count
    """
    return exact_token_count(text)


def trim_text_to_token_limit(text: str, max_tokens: int, keep: str = "end") -> str:
    """Trim text to token limit (now exact for backwards compatibility).
    
    Args:
        text: Input text to trim
        max_tokens: Maximum number of tokens to keep
        keep: Which part to keep ('start' or 'end')
        
    Returns:
        Trimmed text
    """
    return trim_text_to_token_limit_exact(text, max_tokens=max_tokens, keep=keep)


