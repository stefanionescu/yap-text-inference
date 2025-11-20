from __future__ import annotations

import os
from argparse import ArgumentParser, Namespace
from collections.abc import Mapping
from typing import Any

from test.config import (
    DEFAULT_SERVER_WS_URL,
    CHAT_REPEAT_PENALTY_DEFAULT,
    CHAT_TEMPERATURE_DEFAULT,
    CHAT_TOP_K_DEFAULT,
    CHAT_TOP_P_DEFAULT,
)


def add_connection_args(
    parser: ArgumentParser,
    *,
    server_help: str | None = None,
    include_api_key: bool = True,
) -> None:
    """
    Register standard connection flags for test utilities.

    - ``--server`` defaults to ``SERVER_WS_URL`` env or ``DEFAULT_SERVER_WS_URL``.
    - ``--api-key`` defaults to ``TEXT_API_KEY`` env (if ``include_api_key``).
    """

    default_server = os.getenv("SERVER_WS_URL", DEFAULT_SERVER_WS_URL)
    parser.add_argument(
        "--server",
        default=default_server,
        help=server_help
        or f"WebSocket server URL (default env SERVER_WS_URL or {DEFAULT_SERVER_WS_URL})",
    )
    if include_api_key:
        parser.add_argument(
            "--api-key",
            default=os.getenv("TEXT_API_KEY"),
            help="API key for authentication (default env TEXT_API_KEY)",
        )


def add_sampling_args(parser: ArgumentParser) -> None:
    """Register standard sampling override knobs shared across test clients."""
    parser.add_argument(
        "--temperature",
        type=float,
        help=f"Sampling temperature override (default server value: {CHAT_TEMPERATURE_DEFAULT})",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        dest="top_p",
        help=f"Nucleus sampling probability (default server value: {CHAT_TOP_P_DEFAULT})",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        dest="top_k",
        help=f"Top-k sampling cap (default server value: {CHAT_TOP_K_DEFAULT})",
    )
    parser.add_argument(
        "--repeat-penalty",
        type=float,
        dest="repeat_penalty",
        help=f"Repetition penalty (default server value: {CHAT_REPEAT_PENALTY_DEFAULT})",
    )


def build_sampling_payload(args: Mapping[str, Any] | Namespace) -> dict[str, float | int]:
    """Extract CLI sampling overrides into the payload format expected by the server."""
    if not isinstance(args, Mapping):
        args = vars(args)
    payload: dict[str, float | int] = {}
    for field in ("temperature", "top_p", "top_k", "repeat_penalty"):
        value = args.get(field)
        if value is not None:
            payload[field] = value
    return payload


__all__ = ["add_connection_args", "add_sampling_args", "build_sampling_payload"]

