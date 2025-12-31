"""Request and task tracking for session management.

This module handles the tracking of active requests and asyncio tasks:

1. Request ID Tracking:
   - active_request_id: The current chat generation request
   - tool_request_id: The current tool/classifier request
   - CANCELLED_SENTINEL: Special value marking cancelled sessions

2. Task Management:
   - track_task: Register an asyncio.Task for a session
   - has_running_task: Check if a session has active work
   - Done callbacks to auto-clear completed tasks

3. Cancellation:
   - is_request_cancelled: Check if a request was superseded
   - cancel_session_requests: Mark session as cancelled
   - cleanup_session_requests: Extract and clear request IDs

These utilities support clean cancellation of in-flight generation
and proper cleanup when connections close.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import SessionState


# Special sentinel value indicating the session was explicitly cancelled
CANCELLED_SENTINEL = "__CANCELLED__"


def set_active_request(state: "SessionState", request_id: str) -> None:
    """Set the active chat request ID for the session."""
    state.active_request_id = request_id


def set_tool_request(state: "SessionState", request_id: str) -> None:
    """Set the active tool request ID for the session."""
    state.tool_request_id = request_id


def get_tool_request_id(state: "SessionState | None") -> str:
    """Get the current tool request ID, or empty string if none."""
    return state.tool_request_id or "" if state else ""


def clear_tool_request_id(state: "SessionState") -> None:
    """Clear the tool request ID."""
    state.tool_request_id = None


def is_request_cancelled(state: "SessionState | None", request_id: str) -> bool:
    """Check if a request has been cancelled or superseded.
    
    A request is considered cancelled if:
    - The session doesn't exist
    - The session's active_request_id is CANCELLED_SENTINEL
    - The session's active_request_id differs from the given request_id
    
    Args:
        state: The session state, or None if session doesn't exist.
        request_id: The request ID to check.
        
    Returns:
        True if the request should be considered cancelled.
    """
    if not state:
        return True
    active = state.active_request_id
    if active == CANCELLED_SENTINEL:
        return True
    if not active:
        return False
    return active != request_id


def track_task(
    state: "SessionState",
    task: asyncio.Task,
    get_state_callback: callable,
) -> None:
    """Register an asyncio.Task for the session with auto-cleanup.
    
    When the task completes (success, error, or cancel), the callback
    clears the task reference if it's still the current task.
    
    Args:
        state: The session state to track the task on.
        task: The asyncio.Task to track.
        get_state_callback: A callback that returns the current state for
            the session (used in the done callback to handle potential
            session recreation).
    """
    state.task = task

    def _clear_task(completed: asyncio.Task) -> None:
        current = get_state_callback()
        if current and current.task is completed:
            current.task = None
            current.touch()

    task.add_done_callback(_clear_task)


def has_running_task(state: "SessionState | None") -> bool:
    """Check if the session has a running task."""
    return bool(state and state.task and not state.task.done())


def cancel_session_requests(state: "SessionState") -> None:
    """Mark the session as cancelled and cancel any running task.
    
    Sets active_request_id to CANCELLED_SENTINEL so that any in-flight
    generation knows to stop yielding tokens.
    """
    state.active_request_id = CANCELLED_SENTINEL
    if state.task and not state.task.done():
        state.task.cancel()


def cleanup_session_requests(state: "SessionState | None") -> dict[str, str]:
    """Extract and clear request IDs from the session.
    
    Used during cleanup to capture what requests were active before
    clearing them.
    
    Returns:
        Dict with 'active' and 'tool' keys containing the request IDs
        (empty strings if none were set).
    """
    if not state:
        return {"active": "", "tool": ""}
    active_req = (
        state.active_request_id
        if state.active_request_id not in (None, CANCELLED_SENTINEL)
        else ""
    )
    tool_req = state.tool_request_id or ""
    state.active_request_id = None
    state.tool_request_id = None
    return {"active": active_req, "tool": tool_req}


__all__ = [
    "CANCELLED_SENTINEL",
    "set_active_request",
    "set_tool_request",
    "get_tool_request_id",
    "clear_tool_request_id",
    "is_request_cancelled",
    "track_task",
    "has_running_task",
    "cancel_session_requests",
    "cleanup_session_requests",
]

