"""WebSocket utilities for test clients.

This subpackage provides utilities for WebSocket communication including
connection handling, message parsing, payload building, and stream consumption.
"""

from .message import dispatch_message, iter_messages, parse_message
from .payloads import build_cancel_payload, build_end_payload, build_envelope, build_start_payload
from .stream import consume_stream, create_tracker, finalize_metrics, record_token, record_toolcall
from .ws import connect_with_retries, recv_raw, send_client_end, with_api_key

__all__ = [
    # message
    "dispatch_message",
    "iter_messages",
    "parse_message",
    # payloads
    "build_cancel_payload",
    "build_end_payload",
    "build_envelope",
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
