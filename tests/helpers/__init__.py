"""Common utilities for test clients (benchmarks and warmups).

This module re-exports the most commonly used symbols from the helpers
submodules. Import from here when you need standard test utilities.
"""

from .cli import (
    add_connection_args,
    add_sampling_args,
    build_sampling_payload,
)
from .env import get_float_env, get_int_env
from .errors import (
    AuthenticationError,
    ConnectionClosedError,
    ConnectionError,
    ConnectionRejectedError,
    IdleTimeoutError,
    InputClosedError,
    InternalServerError,
    InvalidMessageError,
    MessageParseError,
    RateLimitError,
    ServerAtCapacityError,
    ServerError,
    TestClientError,
    ValidationError,
    error_from_close,
    is_idle_timeout_close,
)
from .fmt import (
    bold,
    cyan,
    dim,
    exchange_footer,
    exchange_header,
    format_assistant,
    format_fail,
    format_info,
    format_metrics_inline,
    format_pass,
    format_ttfb_summary,
    format_user,
    green,
    magenta,
    red,
    section_header,
    test_header,
    yellow,
)
from .math import round_ms, secs_to_ms
from .message import dispatch_message, iter_messages, parse_message
from .payloads import SessionContext, build_chat_prompt_payload, build_start_payload
from .prompt import normalize_gender, select_chat_prompt
from .rate import SlidingWindowPacer
from .regex import contains_complete_sentence, has_at_least_n_words
from .results import BenchmarkResult, error_result, success_result
from .setup import setup_repo_path
from .stream import StreamTracker
from .ttfb import TTFBAggregator
from .selection import choose_message
from .ws import connect_with_retries, recv_raw, send_client_end, with_api_key

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
    "RateLimitError",
    "ServerAtCapacityError",
    "ServerError",
    "TestClientError",
    "ValidationError",
    "error_from_close",
    "is_idle_timeout_close",
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
    # math
    "round_ms",
    "secs_to_ms",
    # message
    "dispatch_message",
    "iter_messages",
    "parse_message",
    # payloads
    "SessionContext",
    "build_chat_prompt_payload",
    "build_start_payload",
    # prompt
    "normalize_gender",
    "select_chat_prompt",
    # rate
    "SlidingWindowPacer",
    # regex
    "contains_complete_sentence",
    "has_at_least_n_words",
    # results
    "BenchmarkResult",
    "error_result",
    "success_result",
    # setup
    "setup_repo_path",
    # stream
    "StreamTracker",
    # ttfb
    "TTFBAggregator",
    # selection
    "choose_message",
    # ws
    "connect_with_retries",
    "recv_raw",
    "send_client_end",
    "with_api_key",
]
