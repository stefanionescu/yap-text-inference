"""WebSocket and session management handlers.

This package provides the infrastructure for handling client connections:

auth.py:
    API key validation for HTTP and WebSocket connections.
    Supports both query parameter and header-based authentication.

connections.py:
    Manages WebSocket connection slots with semaphore-based limiting.
    Prevents server overload by rejecting connections at capacity.

rate_limit.py:
    Sliding window rate limiter for per-connection message throttling.
    Protects against spam and abuse.

session/:
    Session state management including:
    - Conversation history (history.py)
    - Persona configuration (state.py)
    - Request tracking and cancellation (manager.py)
    - Time utilities (time.py)

websocket/:
    WebSocket message routing and lifecycle:
    - Connection lifecycle with idle timeout (lifecycle.py)
    - Message parsing and validation (parser.py)
    - Error response helpers (errors.py)
    - Streaming utilities (helpers.py)
    - Main connection handler (manager.py)
"""
