"""Engine lifecycle exceptions.

These exceptions are raised during engine initialization and shutdown
to signal that operations cannot proceed.
"""

from .shutdown_error import EngineShutdownError
from .not_ready_error import EngineNotReadyError

__all__ = ["EngineNotReadyError", "EngineShutdownError"]
