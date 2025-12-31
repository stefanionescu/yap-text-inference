"""Session request abortion utilities.

This module provides the abort_session_requests helper function that handles
clean cancellation of active generation requests. It:

1. Marks the session as cancelled to reject new tokens
2. Cancels any tracked asyncio.Task
3. Best-effort aborts the engine request (if chat is deployed)
4. Optionally clears all session state

This is separated from the main SessionHandler to:
- Keep abort logic self-contained and testable
- Avoid circular imports when aborting from websocket handlers
- Clarify that this is a helper operating ON sessions, not part of sessions
"""

from __future__ import annotations

from src.config import DEPLOY_CHAT
from ..instances import session_handler


async def abort_session_requests(
    session_id: str | None,
    *,
    clear_state: bool = False,
) -> dict[str, str]:
    """Cancel tracked session requests and best-effort abort engine work.
    
    This function handles graceful cancellation of in-flight requests:
    1. Sets the session's active_request_id to CANCELLED_SENTINEL
    2. Cancels any tracked asyncio.Task
    3. Calls engine.abort() for the active request (if deployed)
    4. Optionally clears all session state
    
    Args:
        session_id: The session to abort requests for. If None, returns empty.
        clear_state: If True, also clears all session data after aborting.
        
    Returns:
        Dict with 'active' and 'tool' keys containing the aborted request IDs.
        Empty strings if no requests were active.
    """
    if not session_id:
        return {"active": "", "tool": ""}

    session_handler.cancel_session_requests(session_id)
    req_info = session_handler.cleanup_session_requests(session_id)

    if DEPLOY_CHAT and req_info.get("active"):
        try:
            from src.engines import get_engine

            await (await get_engine()).abort(req_info["active"])
        except Exception:  # noqa: BLE001 - best effort
            pass

    if clear_state:
        session_handler.clear_session_state(session_id)

    return req_info


__all__ = ["abort_session_requests"]

