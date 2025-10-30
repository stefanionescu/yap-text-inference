from __future__ import annotations

import os


def with_api_key(url: str, api_key_env: str = "YAP_TEXT_API_KEY", default_key: str = "yap_token") -> str:
    """Append API key as a query parameter to the WebSocket URL.

    This keeps client code consistent across tools; it does not validate the key.
    """
    api_key = os.getenv(api_key_env, default_key)
    return f"{url}&api_key={api_key}" if "?" in url else f"{url}?api_key={api_key}"


