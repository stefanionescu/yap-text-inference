"""WebSocket utilities for test clients.

This subpackage provides utilities for WebSocket communication including
connection handling, message parsing, payload building, and stream consumption.
"""

from .payloads import build_start_payload
from .message import iter_messages, parse_message, dispatch_message
from .ws import recv_raw, with_api_key, send_client_end, connect_with_retries
from .stream import record_token, consume_stream, create_tracker, record_toolcall, finalize_metrics

__all__ = [
    # message
    "dispatch_message",
    "iter_messages",
    "parse_message",
    # payloads
    "build_start_payload",
    # stream
    "consume_stream",
    "create_tracker",
    "finalize_metrics",
    "record_token",
    "record_toolcall",
    # ws
    "connect_with_retries",
    "recv_raw",
    "send_client_end",
    "with_api_key",
]

