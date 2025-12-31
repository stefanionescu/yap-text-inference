"""Hard-coded messages for control function responses.

These messages are returned instead of calling the chat model for
control functions like switch_gender, switch_personality, etc.

Messages are cycled per session to ensure variety - once a message
is used, it's temporarily removed from the pool until all messages
have been used, then the pool resets.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from ...config.chat import CONTROL_FUNCTION_MESSAGES

if TYPE_CHECKING:
    from ...handlers.session.state import SessionState


def pick_control_message(state: SessionState) -> str:
    """Pick a random control message, cycling through all before repeating.
    
    Each message is used once before the pool resets. This ensures
    variety in responses across a session.
    
    Args:
        state: Session state containing used message tracking
        
    Returns:
        A randomly selected message from the available pool
    """
    used = state.used_control_messages
    available = [msg for msg in CONTROL_FUNCTION_MESSAGES if msg not in used]
    
    # Reset pool if all messages have been used
    if not available:
        used.clear()
        available = list(CONTROL_FUNCTION_MESSAGES)
    
    message = random.choice(available)
    used.add(message)
    return message


__all__ = ["pick_control_message"]
