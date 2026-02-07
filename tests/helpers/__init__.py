"""Common utilities for test clients (benchmarks and warmups).

This module re-exports the most commonly used symbols from the helpers
submodules. Import from here when you need standard test utilities.
"""

from .setup import setup_repo_path
from .rate import SlidingWindowPacer
from .selection import choose_message
from .env import get_int_env, get_float_env
from .prompt import normalize_gender, select_chat_prompt
from .concurrency import distribute_requests, sanitize_concurrency
from .regex import word_count_at_least, contains_complete_sentence
from .cli import add_sampling_args, add_connection_args, build_sampling_payload
from .metrics import (
    round_ms,
    secs_to_ms,
    record_ttfb,
    error_result,
    result_to_dict,
    success_result,
    has_ttfb_samples,
    emit_ttfb_summary,
    create_ttfb_aggregator,
)
from .websocket import (
    recv_raw,
    record_token,
    with_api_key,
    iter_messages,
    parse_message,
    consume_stream,
    create_tracker,
    record_toolcall,
    send_client_end,
    dispatch_message,
    finalize_metrics,
    build_start_payload,
    connect_with_retries,
)
from .fmt import (
    dim,
    red,
    bold,
    cyan,
    green,
    yellow,
    magenta,
    format_fail,
    format_info,
    format_pass,
    format_user,
    test_header,
    section_header,
    exchange_footer,
    exchange_header,
    format_assistant,
    format_ttfb_summary,
    format_metrics_inline,
)
from .errors import (
    ServerError,
    StreamError,
    RateLimitError,
    ConnectionError,
    TestClientError,
    ValidationError,
    IdleTimeoutError,
    InputClosedError,
    MessageParseError,
    AuthenticationError,
    InternalServerError,
    InvalidMessageError,
    PromptSelectionError,
    ConnectionClosedError,
    ServerAtCapacityError,
    ConnectionRejectedError,
)

__all__ = [
    # cli
    "add_connection_args",
    "add_sampling_args",
    "build_sampling_payload",
    # env
    "get_float_env",
    "get_int_env",
    # errors
    "AuthenticationError",
    "ConnectionClosedError",
    "ConnectionError",
    "ConnectionRejectedError",
    "IdleTimeoutError",
    "InputClosedError",
    "InternalServerError",
    "InvalidMessageError",
    "MessageParseError",
    "PromptSelectionError",
    "RateLimitError",
    "ServerAtCapacityError",
    "ServerError",
    "StreamError",
    "TestClientError",
    "ValidationError",
    # fmt
    "bold",
    "cyan",
    "dim",
    "exchange_footer",
    "exchange_header",
    "format_assistant",
    "format_fail",
    "format_info",
    "format_metrics_inline",
    "format_pass",
    "format_ttfb_summary",
    "format_user",
    "green",
    "magenta",
    "red",
    "section_header",
    "test_header",
    "yellow",
    # metrics
    "create_ttfb_aggregator",
    "emit_ttfb_summary",
    "error_result",
    "has_ttfb_samples",
    "record_ttfb",
    "result_to_dict",
    "round_ms",
    "secs_to_ms",
    "success_result",
    # prompt
    "normalize_gender",
    "select_chat_prompt",
    # rate
    "SlidingWindowPacer",
    # regex
    "contains_complete_sentence",
    "word_count_at_least",
    # setup
    "setup_repo_path",
    # concurrency
    "distribute_requests",
    "sanitize_concurrency",
    # selection
    "choose_message",
    # websocket
    "build_start_payload",
    "connect_with_retries",
    "consume_stream",
    "create_tracker",
    "dispatch_message",
    "finalize_metrics",
    "iter_messages",
    "parse_message",
    "record_token",
    "record_toolcall",
    "recv_raw",
    "send_client_end",
    "with_api_key",
]
