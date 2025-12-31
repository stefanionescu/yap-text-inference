"""Chat-related message handlers and prompt building.

This subpackage contains:
- prompt.py: Handler for mid-session persona/prompt updates
- builder.py: Chat prompt construction using tokenizer templates
"""

from .builder import build_chat_prompt_with_prefix, build_chat_warm_prompt
from .prompt import handle_chat_prompt

__all__ = [
    "build_chat_prompt_with_prefix",
    "build_chat_warm_prompt",
    "handle_chat_prompt",
]

