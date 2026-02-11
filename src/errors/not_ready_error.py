"""Engine-not-ready lifecycle exception."""


class EngineNotReadyError(Exception):
    """Raised when the engine is not ready to serve requests."""


__all__ = ["EngineNotReadyError"]
