"""Clean, readable output formatting for test utilities.

This module provides consistent formatting helpers for displaying test
results in a readable, scannable format across all test scripts.
"""

from __future__ import annotations

import sys
from typing import Any

# ANSI color codes (disabled if not a tty)
_USE_COLOR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    """Wrap text in ANSI color codes if output is a tty."""
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def dim(text: str) -> str:
    return _c("2", text)


def bold(text: str) -> str:
    return _c("1", text)


def green(text: str) -> str:
    return _c("32", text)


def red(text: str) -> str:
    return _c("31", text)


def cyan(text: str) -> str:
    return _c("36", text)


def yellow(text: str) -> str:
    return _c("33", text)


def magenta(text: str) -> str:
    return _c("35", text)


# ============================================================================
# Visual separators
# ============================================================================

def section_header(title: str, width: int = 60) -> str:
    """Create a prominent section header."""
    padding = width - len(title) - 4
    left = padding // 2
    right = padding - left
    return bold(f"{'─' * left}[ {title} ]{'─' * right}")


def test_header(name: str) -> str:
    """Create a test case header."""
    return f"\n{section_header(name)}"


def exchange_header(idx: int | None = None, persona: str | None = None, gender: str | None = None) -> str:
    """Create an exchange header with optional persona info."""
    parts = []
    if idx is not None:
        parts.append(f"#{idx:02d}")
    if persona and gender:
        parts.append(f"{persona}/{gender}")
    elif persona:
        parts.append(persona)
    elif gender:
        parts.append(gender)
    
    label = " ".join(parts) if parts else "Exchange"
    return dim(f"┌─ {label} {'─' * (50 - len(label))}")


def exchange_footer() -> str:
    """Create an exchange footer."""
    return dim("└" + "─" * 55)


# ============================================================================
# Message formatting
# ============================================================================

def format_user(text: str, max_len: int = 80) -> str:
    """Format a user message."""
    display = text if len(text) <= max_len else text[:max_len-3] + "..."
    return f"{cyan('USER')}  {display}"


def format_assistant(text: str, max_len: int = 120) -> str:
    """Format an assistant message."""
    display = text if len(text) <= max_len else text[:max_len-3] + "..."
    return f"{magenta('ASST')}  {display}"


def format_metrics_inline(metrics: dict[str, Any]) -> str:
    """Format metrics as a compact inline string."""
    parts = []
    
    ttfb = metrics.get("ttfb_ms") or metrics.get("ttfb_chat_ms")
    if ttfb is not None:
        parts.append(f"ttfb={ttfb:.0f}ms")
    
    tool_ttfb = metrics.get("ttfb_toolcall_ms")
    if tool_ttfb is not None:
        parts.append(f"tool={tool_ttfb:.0f}ms")
    
    first_3 = metrics.get("time_to_first_3_words_ms")
    if first_3 is not None:
        parts.append(f"3w={first_3:.0f}ms")
    
    first_sent = metrics.get("time_to_first_complete_sentence_ms")
    if first_sent is not None:
        parts.append(f"sent={first_sent:.0f}ms")
    
    total = metrics.get("total_ms")
    if total is not None:
        parts.append(f"total={total:.0f}ms")
    
    chunks = metrics.get("chunks")
    chars = metrics.get("chars")
    if chunks is not None and chars is not None:
        parts.append(f"{chunks}chunks/{chars}chars")
    
    return dim(" · ".join(parts)) if parts else ""


# ============================================================================
# Test result formatting
# ============================================================================

def format_pass(label: str) -> str:
    """Format a passing test result."""
    return f"{green('✓ PASS')}  {label}"


def format_fail(label: str, reason: str = "") -> str:
    """Format a failing test result."""
    suffix = f": {reason}" if reason else ""
    return f"{red('✗ FAIL')}  {label}{suffix}"


def format_info(text: str) -> str:
    """Format informational text."""
    return dim(f"  {text}")


# ============================================================================
# TTFB summary formatting
# ============================================================================

def format_ttfb_summary(
    kind: str,
    stats: dict[str, float | int],
    label: str = "TTFB",
) -> str:
    """Format TTFB summary statistics in a readable table row."""
    parts = [
        f"{bold(label)} {yellow(kind):>4}",
        f"first={stats['first']:>6.0f}ms",
        f"avg={stats['average']:>6.0f}ms",
        f"p50={stats['p50']:>6.0f}ms",
        f"p90={stats['p90']:>6.0f}ms",
        f"p95={stats['p95']:>6.0f}ms",
        dim(f"(n={stats['count']})"),
    ]
    return "  ".join(parts)


# ============================================================================
# Connection test formatting
# ============================================================================

def connection_test_header(name: str) -> str:
    """Create a connection test section header."""
    return f"\n{bold(f'▶ {name.upper()}')} connection test"


def connection_status(label: str, message: str) -> str:
    """Format a connection status update."""
    return dim(f"  [{label}] {message}")


def connection_pass(label: str) -> str:
    """Format a connection test pass."""
    return f"  {green('✓')} [{label}] {green('PASS')}"


def connection_fail(label: str, reason: str) -> str:
    """Format a connection test failure."""
    return f"  {red('✗')} [{label}] {red('FAIL')}: {reason}"


__all__ = [
    # Colors
    "dim", "bold", "green", "red", "cyan", "yellow", "magenta",
    # Separators
    "section_header", "test_header", "exchange_header", "exchange_footer",
    # Messages
    "format_user", "format_assistant", "format_metrics_inline",
    # Results
    "format_pass", "format_fail", "format_info",
    # TTFB
    "format_ttfb_summary",
    # Connections
    "connection_test_header", "connection_status", "connection_pass", "connection_fail",
]

