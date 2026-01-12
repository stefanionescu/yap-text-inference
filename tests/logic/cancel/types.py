"""Result types for cancel test phases and clients.

This module defines dataclasses that capture the outcome of each test phase
(cancel, drain, recovery) and client type (canceling client, normal client).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CancelPhaseResult:
    """Result from the cancel phase of the test.
    
    Captures whether the cancel was acknowledged correctly and any
    tokens/chars received before cancellation.
    """

    passed: bool
    cancelled: bool
    tokens_received: int
    chars_received: int
    ack_seen: bool
    error: str | None = None


@dataclass
class DrainPhaseResult:
    """Result from the drain phase - verifying no spurious messages.
    
    After cancel acknowledgement, we wait to ensure no additional
    messages arrive from the server. Any message is a failure.
    """

    passed: bool
    spurious_messages: int
    error: str | None = None


@dataclass
class RecoveryPhaseResult:
    """Result from the recovery phase of the test.
    
    Captures whether a follow-up request after cancel completed
    successfully with a full response.
    """

    passed: bool
    response_text: str
    metrics: dict[str, Any]
    error: str | None = None


@dataclass
class CancelClientResult:
    """Combined result for the client that performs cancel.
    
    Aggregates results from all three phases: cancel, drain, and recovery.
    """

    cancel_phase: CancelPhaseResult
    drain_phase: DrainPhaseResult
    recovery_phase: RecoveryPhaseResult

    @property
    def all_passed(self) -> bool:
        """Check if all phases passed."""
        return (
            self.cancel_phase.passed
            and self.drain_phase.passed
            and self.recovery_phase.passed
        )


@dataclass
class NormalClientResult:
    """Result for a client that completes normally without canceling.
    
    These clients run inference to completion and wait for the
    canceling client's recovery before disconnecting.
    """

    client_id: int
    passed: bool
    response_text: str
    metrics: dict[str, Any]
    error: str | None = None


__all__ = [
    "CancelPhaseResult",
    "DrainPhaseResult",
    "RecoveryPhaseResult",
    "CancelClientResult",
    "NormalClientResult",
]
