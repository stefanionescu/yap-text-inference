"""Session management helpers.

This package provides session state management for the inference server.
Sessions track per-connection data including:

- Persona configuration (gender, personality, custom prompts)
- Conversation history and turn tracking
- Active request IDs for cancellation
- Rate limiting state for prompt updates
- Screen prefix customization

Key components:
- SessionHandler: Central session coordinator
- session_handler: Global singleton instance (from handlers.instances)
- abort_session_requests: Clean request cancellation
"""

from ..instances import session_handler
from .abort import abort_session_requests
from .manager import SessionHandler

__all__ = ["SessionHandler", "session_handler", "abort_session_requests"]
