"""Secrets and authentication related configuration."""

import os

# API key used for authenticated public surfaces such as /ws.
TEXT_API_KEY: str | None = os.getenv("TEXT_API_KEY")


__all__ = ["TEXT_API_KEY"]
