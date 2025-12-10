from __future__ import annotations

import os
from argparse import ArgumentParser, Namespace
from collections.abc import Mapping
from typing import Any

from tests.config import (
    DEFAULT_SERVER_WS_URL,
    CHAT_REPETITION_PENALTY_DEFAULT,
    CHAT_PRESENCE_PENALTY_DEFAULT,
    CHAT_FREQUENCY_PENALTY_DEFAULT,
    CHAT_TEMPERATURE_DEFAULT,
    CHAT_TOP_K_DEFAULT,
    CHAT_TOP_P_DEFAULT,
    CLASSIFIER_MODE,
)
from tests.helpers.prompt import PROMPT_MODE_BOTH, PROMPT_MODE_CHOICES, normalize_prompt_mode


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


PROMPT_MODE_ENV_VAR = "PROMPT_MODE"


def add_prompt_mode_arg(
    parser: ArgumentParser,
    *,
    default: str = PROMPT_MODE_BOTH,
    env_var: str = PROMPT_MODE_ENV_VAR,
) -> None:
    """
    Register a flag controlling which prompts get sent to the server.

    Respects ``env_var`` (default: PROMPT_MODE) for overrides.
    """

    env_override = os.getenv(env_var)
    resolved_default = default
    if env_override:
        try:
            resolved_default = normalize_prompt_mode(env_override)
        except ValueError:
            resolved_default = default

    parser.add_argument(
        "--prompt-mode",
        choices=PROMPT_MODE_CHOICES,
        default=resolved_default,
        help=(
            "Which prompts to send on connection start "
            f"(default: {resolved_default}, env {env_var} overrides)"
        ),
    )


CLASSIFIER_MODE_ENV_VAR = "CLASSIFIER_MODE"


def add_classifier_mode_arg(
    parser: ArgumentParser,
    *,
    env_var: str = CLASSIFIER_MODE_ENV_VAR,
) -> None:
    """
    Register a flag to indicate classifier mode (no tool prompt required).

    Respects ``env_var`` (default: CLASSIFIER_MODE) for overrides.
    """
    parser.add_argument(
        "--classifier-mode",
        action="store_true",
        default=CLASSIFIER_MODE,
        help=(
            "Classifier mode: server uses classifier model, no tool_prompt required "
            f"(default: {'True' if CLASSIFIER_MODE else 'False'}, env {env_var} overrides)"
        ),
    )


__all__ = [
    "add_connection_args",
    "add_sampling_args",
    "add_prompt_mode_arg",
    "add_classifier_mode_arg",
    "build_sampling_payload",
]

