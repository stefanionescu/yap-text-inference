"""Secrets and authentication related configuration."""

import os

# API Key for authentication (all endpoints except /healthz)
# Validated at runtime by helpers/validation.py
TEXT_API_KEY: str | None = os.getenv("TEXT_API_KEY")


__all__ = ["TEXT_API_KEY"]


