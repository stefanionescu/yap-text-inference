"""Default tool regression prompts and expected outcomes."""
# ruff: noqa: E501  # Test data - long strings are intentional

from .tool_types import ToolDefaultEntry
from .tool_edge import TOOL_MESSAGES as TOOL_EDGE_MESSAGES
from .tool_basic import TOOL_MESSAGES as TOOL_BASIC_MESSAGES
from .tool_long_a import TOOL_MESSAGES as TOOL_LONG_A_MESSAGES
from .tool_long_b import TOOL_MESSAGES as TOOL_LONG_B_MESSAGES
from .tool_visual import TOOL_MESSAGES as TOOL_VISUAL_MESSAGES
from .tool_natural import TOOL_MESSAGES as TOOL_NATURAL_MESSAGES
from .tool_multiturn_a import TOOL_MESSAGES as TOOL_MULTITURN_A_MESSAGES
from .tool_multiturn_b import TOOL_MESSAGES as TOOL_MULTITURN_B_MESSAGES

TOOL_DEFAULT_MESSAGES: list[ToolDefaultEntry] = [
    *TOOL_BASIC_MESSAGES,
    *TOOL_VISUAL_MESSAGES,
    *TOOL_EDGE_MESSAGES,
    *TOOL_MULTITURN_A_MESSAGES,
    *TOOL_MULTITURN_B_MESSAGES,
    *TOOL_LONG_A_MESSAGES,
    *TOOL_LONG_B_MESSAGES,
    *TOOL_NATURAL_MESSAGES,
]

__all__ = ["TOOL_DEFAULT_MESSAGES"]
