"""Deployment mode configuration.

Defines what to deploy (chat, tool, or both) and model selections.
"""

from __future__ import annotations

import os


# Deployment mode: 'both', 'chat', or 'tool'
DEPLOY_MODELS = (os.getenv("DEPLOY_MODELS", "both") or "both").lower()
DEPLOY_CHAT = DEPLOY_MODELS in ("both", "chat")
DEPLOY_TOOL = DEPLOY_MODELS in ("both", "tool")

# Model selections
CHAT_MODEL = os.getenv("CHAT_MODEL")
TOOL_MODEL = os.getenv("TOOL_MODEL")


__all__ = [
    "DEPLOY_MODELS",
    "DEPLOY_CHAT",
    "DEPLOY_TOOL",
    "CHAT_MODEL",
    "TOOL_MODEL",
]

