"""Start message handling.

This package handles the 'start' WebSocket message type which initiates
new conversation turns. It includes:

- handler: Main message handler and validation
- dispatch: Execution path routing based on deployment config
- sampling: Sampling parameter extraction and validation
"""

from .handler import handle_start_message
from .sampling import extract_sampling_overrides
from .dispatch import StartPlan, dispatch_execution

__all__ = [
    "handle_start_message",
    "StartPlan",
    "dispatch_execution",
    "extract_sampling_overrides",
]

