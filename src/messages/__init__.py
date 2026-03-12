"""WebSocket message type handlers for the inference server.

This package provides handlers for different WebSocket message types:

turn.py:
    Unified turn planner/handler for both 'start' and 'message' commands.
    It validates payloads, builds a TurnPlan, and dispatches execution.

start/:
    Shared turn sub-components:
    - dispatch.py: execution path routing
    - history.py: history bootstrap + utterance trimming
    - sampling.py: sampling parameter extraction

cancel.py:
    Handles request cancellation during streaming. Aborts the
    active generation request and cleans up state.

validators.py:
    Input validation utilities shared across message handlers.
    Validates sampling parameters, token limits, and field formats.

sanitize/:
    Text sanitization for prompts and streamed output:
    - prompt.py: Clean incoming prompts
    - stream.py: Normalize generated text in real-time
    - common.py: Shared sanitization patterns

Import from submodules directly to avoid circular imports:
    from src.messages.turn import handle_turn_message
"""
