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


def trim_history_for_tool_sharing(history_text: str, tool_history_tokens: int, exact: bool = True) -> str:
    """Trim history text specifically for tool model KV cache sharing.
    
    This implements rolling eviction by keeping only the most recent tokens
    that can be shared with the chat model's KV cache.
    
    Args:
        history_text: Full conversation history
        tool_history_tokens: Maximum tokens to keep for tool model
        exact: Whether to use exact tokenization
        
    Returns:
        Trimmed history text for tool model consumption
    """
    if not history_text.strip():
        return ""
        
    # Use message-boundary-aware trimming for tool model
    return trim_history_preserve_messages(history_text, tool_history_tokens, exact)


def trim_history_preserve_messages(history_text: str, max_tokens: int, exact: bool = True) -> str:
    """Trim history while preserving complete message boundaries.
    
    If a message doesn't fit entirely within the token limit, it is fully evicted
    rather than keeping a partial/cropped message.
    
    Args:
        history_text: Full conversation history
        max_tokens: Maximum tokens to keep
        exact: Whether to use exact tokenization
        
    Returns:
        Trimmed history with complete messages only
    """
    if not history_text.strip():
        return ""
    
    # Common message boundary patterns to split on
    # Priority order: most specific to least specific
    boundary_patterns = [
        '\nUser: ',     # "User: message"
        '\nAssistant: ', # "Assistant: response"  
        '\n\nUser: ',   # Double newline variants
        '\n\nAssistant: ',
        '\n\n',         # Double newlines (paragraph breaks)
        '\n',           # Single newlines (fallback)
    ]
    
    # Find the best boundary pattern that exists in the text
    chosen_pattern = None
    for pattern in boundary_patterns:
        if pattern in history_text:
            chosen_pattern = pattern
            break
    
    if not chosen_pattern:
        # No recognizable patterns, fallback to regular token trimming
        if exact:
            return trim_text_to_token_limit_exact(history_text, max_tokens, keep="end")
        else:
            return trim_text_to_token_limit(history_text, max_tokens, keep="end")
    
    # Split by the chosen pattern and work backwards from the end
    parts = history_text.split(chosen_pattern)
    if len(parts) <= 1:
        # Edge case: only one part, use regular trimming
        if exact:
            return trim_text_to_token_limit_exact(history_text, max_tokens, keep="end")
        else:
            return trim_text_to_token_limit(history_text, max_tokens, keep="end")
    
    # Reconstruct from the end, ensuring we don't exceed token limit
    result_parts = []
    current_tokens = 0
    
    # Start from the last part (most recent) and work backwards
    for i in range(len(parts) - 1, -1, -1):
        part = parts[i]
        
        # For non-first parts, we need to include the separator
        test_part = part if i == len(parts) - 1 else chosen_pattern + part
        
        # Count tokens for this part
        if exact:
            part_tokens = exact_token_count(test_part)
        else:
            part_tokens = approx_token_count(test_part)
        
        # Check if adding this part would exceed the limit
        if current_tokens + part_tokens > max_tokens:
            # This message doesn't fit - stop here (don't include partial)
            break
            
        # Add this part to the beginning of our result
        result_parts.insert(0, part)
        current_tokens += part_tokens
    
    if not result_parts:
        # Nothing fit - return empty string rather than partial message
        return ""
    
    # Reconstruct the text with proper separators
    result = result_parts[0]  # First part doesn't need separator
    for part in result_parts[1:]:
        result += chosen_pattern + part
        
    return result.strip()


