"""vLLM Quantization Package (AWQ via llmcompressor)."""

from .core import AWQQuantizer, CalibrationConfig
from .utils.model_utils import is_awq_dir

__version__ = "1.0.0"

__all__ = [
    "AWQQuantizer",
    "CalibrationConfig", 
    "is_awq_dir",
]
