"""Session management helpers.

Do not re-export session_handler here — it would create a circular import.
"""

from .manager import SessionHandler

__all__ = ["SessionHandler"]
