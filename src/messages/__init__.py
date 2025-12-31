"""WebSocket message type handlers for the inference server.

This package provides handlers for different WebSocket message types:

start/:
    Handles initial conversation start messages. Validates input,
    extracts persona/gender/personality configuration, and initiates
    the tool-then-chat execution flow.
    - handler.py: Main start message handler
    - dispatch.py: Execution path routing
    - sampling.py: Sampling parameter extraction

followup.py:
    Handles subsequent messages within an existing session.
    Validates continuation state and routes to execution.

cancel.py:
    Handles request cancellation during streaming. Aborts the
    active generation request and cleans up state.

chat_prompt.py:
    Handles dynamic persona/prompt updates mid-session. Validates
    rate limits and applies new persona configuration.

validators.py:
    Input validation utilities shared across message handlers.
    Validates sampling parameters, token limits, and field formats.

sanitize/:
    Text sanitization for prompts and streamed output:
    - prompt_sanitizer.py: Clean incoming prompts
    - stream_sanitizer.py: Normalize generated text in real-time
    - common.py: Shared sanitization patterns

warm/:
    Session warmup utilities for priming history and personas
    before the first user message.
"""

from .start import handle_start_message, StartPlan, dispatch_execution

__all__ = [
    "handle_start_message",
    "StartPlan",
    "dispatch_execution",
]
