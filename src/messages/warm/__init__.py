"""Session warmup utilities for priming context before user messages.

This package provides helpers to prepare session state:

warm_history.py:
    Format and trim conversation history for warmup requests.
    Ensures history fits within token budgets.

warm_persona.py:
    Build persona system prompts from session configuration.
    Handles static prefixes and runtime context.

warm_utils.py:
    Shared utilities for warmup message construction.
    Provides prompt assembly helpers.
"""
