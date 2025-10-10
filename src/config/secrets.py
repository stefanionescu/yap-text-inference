"""Secrets and authentication related configuration."""

import os


# API Key for authentication (all endpoints except /healthz)
API_KEY = os.getenv("YAP_API_KEY", "yap_token")


__all__ = ["API_KEY"]


