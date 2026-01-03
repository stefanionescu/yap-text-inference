"""Engine lifecycle exceptions.

These exceptions are raised during engine initialization and shutdown
to signal that operations cannot proceed.
"""


class EngineNotReadyError(Exception):
    """Raised when the engine is not ready to serve requests.
    
    This typically occurs during warmup before the engine has fully
    initialized, or if initialization failed.
    """


class EngineShutdownError(Exception):
    """Raised when operations are attempted on a shutdown engine.
    
    Once an engine has been shut down, it cannot be reused. This error
    signals that a new engine instance must be created.
    """


__all__ = ["EngineNotReadyError", "EngineShutdownError"]

