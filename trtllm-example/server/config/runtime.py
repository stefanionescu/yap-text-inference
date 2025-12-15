import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeSettings:
    """Runtime tuning knobs."""

    # Event loop yield (0.0 keeps behavior identical while allowing tuning)
    yield_sleep_seconds: float = float(os.getenv("YIELD_SLEEP_SECONDS", "0"))
