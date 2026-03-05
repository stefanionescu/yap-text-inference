"""Request and task tracking for session management.

This module handles the tracking of active requests and asyncio tasks:

1. Request ID Tracking:
   - active_request_id: The current chat generation request
   - CANCELLED_SENTINEL: Special value marking cancelled sessions

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

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from src.state.session import SessionState


# Special sentinel value indicating the session was explicitly cancelled
CANCELLED_SENTINEL = "__CANCELLED__"


def is_request_cancelled(state: SessionState | None, request_id: str) -> bool:
    """Check if a request has been cancelled or superseded.

    A request is considered cancelled if:
    - The session doesn't exist
    - The session's active_request_id is CANCELLED_SENTINEL
    - The session's active_request_id differs from the given request_id
    """
    if not state:
        return True
    active = state.active_request_id
    if active == CANCELLED_SENTINEL:
        return True
    if not active:
        return False
    return active != request_id


def has_running_task(state: SessionState | None) -> bool:
    """Check if the session has a running task."""
    return bool(state and state.task and not state.task.done())


def cancel_session_requests(state: SessionState) -> None:
    """Mark the session as cancelled and cancel any running task.

    Sets active_request_id to CANCELLED_SENTINEL so that any in-flight
    generation knows to stop yielding tokens.
    """
    state.active_request_id = CANCELLED_SENTINEL
    if state.task and not state.task.done():
        state.task.cancel()


def cleanup_session_requests(state: SessionState | None) -> dict[str, str]:
    """Extract and clear request IDs from the session."""
    if not state:
        return {"active": ""}
    active_req = "" if state.active_request_id in (None, CANCELLED_SENTINEL) else cast(str, state.active_request_id)
    state.active_request_id = None
    return {"active": active_req}


__all__ = [
    "CANCELLED_SENTINEL",
    "is_request_cancelled",
    "has_running_task",
    "cancel_session_requests",
    "cleanup_session_requests",
]
