"""Centralized priority tiers for AsyncLLMEngine scheduling.

Higher numbers preempt lower numbers when scheduling_policy="priority".
Aligning request priorities across the stack ensures latency-sensitive work
(like tool calls) is not blocked by background warming.
"""

TOOL_REQUEST_PRIORITY = 1
CHAT_REQUEST_PRIORITY = 0
WARM_REQUEST_PRIORITY = -1

__all__ = [
    "TOOL_REQUEST_PRIORITY",
    "CHAT_REQUEST_PRIORITY",
    "WARM_REQUEST_PRIORITY",
]
