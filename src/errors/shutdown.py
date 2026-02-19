"""Engine-shutdown lifecycle exception."""


class EngineShutdownError(Exception):
    """Raised when operations are attempted on a shutdown engine."""


__all__ = ["EngineShutdownError"]
