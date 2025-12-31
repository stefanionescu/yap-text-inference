"""Singleton instances for handler classes.

This module serves as the dedicated assembly point for instantiating
global handler singletons. Per project guidelines, singleton instances
should not be created in the same file as their class definitions.

Instances:
    connections: Global ConnectionHandler for WebSocket concurrency limiting.
    session_handler: Global SessionHandler for session state management.
"""

from .connections import ConnectionHandler
from .session.manager import SessionHandler


# ============================================================================
# Connection Handler
# ============================================================================

connections = ConnectionHandler()


# ============================================================================
# Session Handler
# ============================================================================

session_handler = SessionHandler()


__all__ = [
    "connections",
    "session_handler",
]

