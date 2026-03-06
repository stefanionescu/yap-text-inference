"""Request and task tracking for session management.

This module handles the tracking of active requests and asyncio tasks:

1. Request ID Tracking:
   - active_request_id: The current chat generation request
   - cancel_requested: Cooperative cancellation flag for in-flight streams

2. Task Management:
   - has_running_task: Check if a session has active work

3. Cancellation:
   - is_request_cancelled: Check if a request was superseded
   - cancel_session_requests: Mark session as cancelled
   - cleanup_session_requests: Extract and clear request IDs

These utilities support clean cancellation of in-flight generation
and proper cleanup when connections close.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.state.session import SessionState


def is_request_cancelled(state: SessionState | None, request_id: str) -> bool:
    """Check if a request has been cancelled or superseded.

    A request is considered cancelled if:
    - The session doesn't exist
    - The session has cancel_requested=True
    - The session's active_request_id differs from the given request_id
    """
    if not state:
        return True
    if state.cancel_requested:
        return True
    active = state.active_request_id
    if not active:
        return False
    return active != request_id


def has_running_task(state: SessionState | None) -> bool:
    """Check if the session has a running task."""
    return bool(state and state.active_request_task and not state.active_request_task.done())


def cancel_session_requests(state: SessionState) -> None:
    """Mark the session as cancelled and cancel any running task.

    Sets cancel_requested so any in-flight generation knows to stop yielding
    tokens.
    """
    state.cancel_requested = True
    task = state.active_request_task
    if task and not task.done():
        task.cancel()


def cleanup_session_requests(state: SessionState | None) -> dict[str, str]:
    """Extract and clear request IDs from the session."""
    if not state:
        return {"active": ""}
    active_req = state.active_request_id or ""
    state.active_request_id = None
    state.active_request_task = None
    return {"active": active_req}


__all__ = [
    "is_request_cancelled",
    "has_running_task",
    "cancel_session_requests",
    "cleanup_session_requests",
]
