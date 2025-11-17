"""Secrets and authentication related configuration."""

import os


# API Key for authentication (all endpoints except /healthz)
TEXT_API_KEY = os.getenv("TEXT_API_KEY")
if not TEXT_API_KEY:
    raise ValueError("TEXT_API_KEY environment variable is required")


__all__ = ["TEXT_API_KEY"]


