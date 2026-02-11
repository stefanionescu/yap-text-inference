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

chat.py:
    Chat prompt construction using tokenizer templates.

validators.py:
    Input validation utilities shared across message handlers.
    Validates sampling parameters, token limits, and field formats.

sanitize/:
    Text sanitization for prompts and streamed output:
    - prompt.py: Clean incoming prompts
    - stream.py: Normalize generated text in real-time
    - common.py: Shared sanitization patterns

Import from submodules directly to avoid circular imports:
    from src.messages.start.handler import handle_start_message
    from src.messages.chat import build_chat_prompt_with_prefix
"""
