"""CLI argument helpers for test utilities.

This module provides reusable argparse argument groups shared by all test
scripts. It includes connection args (server URL, API key) and sampling
override args (temperature, top_p, etc.).
"""

from __future__ import annotations

import os
from typing import Any
from collections.abc import Mapping
from argparse import Namespace, ArgumentParser
from tests.config import (
    CHAT_TOP_K_DEFAULT,
    CHAT_TOP_P_DEFAULT,
    DEFAULT_SERVER_WS_URL,
    CHAT_TEMPERATURE_DEFAULT,
    CHAT_PRESENCE_PENALTY_DEFAULT,
    CHAT_FREQUENCY_PENALTY_DEFAULT,
    CHAT_REPETITION_PENALTY_DEFAULT,
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
        help=server_help or f"WebSocket server URL (default env SERVER_WS_URL or {DEFAULT_SERVER_WS_URL})",
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
        "--repetition-penalty",
        type=float,
        dest="repetition_penalty",
        help=f"Repetition penalty (default server value: {CHAT_REPETITION_PENALTY_DEFAULT})",
    )
    parser.add_argument(
        "--presence-penalty",
        type=float,
        dest="presence_penalty",
        help=f"Presence penalty (default server value: {CHAT_PRESENCE_PENALTY_DEFAULT})",
    )
    parser.add_argument(
        "--frequency-penalty",
        type=float,
        dest="frequency_penalty",
        help=f"Frequency penalty (default server value: {CHAT_FREQUENCY_PENALTY_DEFAULT})",
    )
    parser.add_argument(
        "--no-sanitize-output",
        action="store_true",
        dest="no_sanitize_output",
        help="Disable output sanitization/cleanup (default: sanitization enabled)",
    )


def build_sampling_payload(args: Mapping[str, Any] | Namespace) -> dict[str, float | int | bool]:
    """Extract CLI sampling overrides into the payload format expected by the server."""
    if not isinstance(args, Mapping):
        args = vars(args)
    payload: dict[str, float | int | bool] = {}
    for field in ("temperature", "top_p", "top_k", "repetition_penalty", "presence_penalty", "frequency_penalty"):
        value = args.get(field)
        if value is not None:
            payload[field] = value
    # Handle boolean flags
    if args.get("no_sanitize_output"):
        payload["sanitize_output"] = False
    return payload


__all__ = [
    "add_connection_args",
    "add_sampling_args",
    "build_sampling_payload",
]
