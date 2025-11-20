from __future__ import annotations

import os
from argparse import ArgumentParser

from test.config import DEFAULT_SERVER_WS_URL


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


__all__ = ["add_connection_args"]

