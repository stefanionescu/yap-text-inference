"""Deployment mode configuration.

This module determines which components of the inference stack are deployed:
- Chat: Main LLM for conversational AI (vLLM or TRT-LLM)
- Tool: Screenshot intent classifier (PyTorch)

The deployment mode affects:
- Which models are loaded at startup
- GPU memory allocation strategy
- Available WebSocket message handlers

Environment Variables:
    DEPLOY_MODE: Deployment mode (default: 'both')
        - 'both': Deploy chat LLM and tool classifier
        - 'chat': Deploy only the chat LLM
        - 'tool': Deploy only the tool classifier
    
    CHAT_MODEL: HuggingFace model ID or local path for chat
        Example: "mistralai/Mistral-Small-3.2-24B-Instruct-2506"
    
    TOOL_MODEL: HuggingFace model ID or local path for classifier
        Example: "yapwithai/yap-modernbert-screenshot-intent"
"""

from __future__ import annotations

import os
import re


# Pattern for HuggingFace repo IDs: org/model-name or user/model-name
# Used to distinguish remote repos from local paths
HF_REPO_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9._-]+$")


# ============================================================================
# Deployment Mode Selection
# ============================================================================
# Controls which inference components are loaded. This affects memory usage
# and available features.

DEPLOY_MODE = (os.getenv("DEPLOY_MODE", "both") or "both").lower()
DEPLOY_CHAT = DEPLOY_MODE in ("both", "chat")  # Enable chat LLM
DEPLOY_TOOL = DEPLOY_MODE in ("both", "tool")  # Enable tool classifier

# ============================================================================
# Model Selections
# ============================================================================
# These can be HuggingFace model IDs or local filesystem paths

CHAT_MODEL = os.getenv("CHAT_MODEL")  # Required if DEPLOY_CHAT=True
TOOL_MODEL = os.getenv("TOOL_MODEL")  # Required if DEPLOY_TOOL=True


__all__ = [
    "HF_REPO_PATTERN",
    "DEPLOY_MODE",
    "DEPLOY_CHAT",
    "DEPLOY_TOOL",
    "CHAT_MODEL",
    "TOOL_MODEL",
]

