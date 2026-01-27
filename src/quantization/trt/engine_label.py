"""Engine label generation for TRT-LLM models.

This module handles engine label generation for HuggingFace repo organization.
Engine labels encode the GPU architecture, TRT-LLM version, and CUDA version
to ensure compatibility when downloading pre-built engines.

Engine labels follow the format: {sm_arch}_trt-llm-{version}_cuda{version}
Example: sm90_trt-llm-0.17.0_cuda12.8
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from dataclasses import field, dataclass

from src.errors import EngineLabelError

from .detection import detect_gpu_name, detect_cuda_version, detect_tensorrt_llm_version

# ============================================================================
# Environment Helpers
# ============================================================================

def _env_int(name: str, default: int | None) -> int | None:
    """Get int from env var, handling empty strings."""
    val = os.getenv(name, "")
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    """Get string from env var, handling empty strings."""
    val = os.getenv(name, "")
    return val if val else default


# ============================================================================
# Environment Info
# ============================================================================

@dataclass
class EnvironmentInfo:
    """Container for environment-detected build information.
    
    Holds the GPU architecture, TRT-LLM version, and CUDA version
    needed to generate engine labels and collect build metadata.
    """

    sm_arch: str
    trt_version: str
    cuda_version: str
    gpu_name: str = field(default_factory=detect_gpu_name)

    @classmethod
    def from_env(cls) -> EnvironmentInfo:
        """Load environment info, raising EngineLabelError if required vars missing."""
        sm_arch = os.getenv("GPU_SM_ARCH")
        if not sm_arch:
            raise EngineLabelError(
                "GPU_SM_ARCH not set. This should be exported by gpu_init_detection() "
                "in scripts/lib/common/gpu_detect.sh."
            )

        trt_version = os.getenv("TRT_VERSION") or detect_tensorrt_llm_version()
        if not trt_version or trt_version == "unknown":
            raise EngineLabelError(
                "TRT_VERSION not set and tensorrt_llm not importable. "
                "This should be set in scripts/lib/env/trt.sh."
            )

        cuda_version = os.getenv("CUDA_VERSION") or detect_cuda_version()
        if not cuda_version or cuda_version == "unknown":
            raise EngineLabelError(
                "CUDA_VERSION not set and nvcc not found. "
                "Ensure CUDA is installed or CUDA_VERSION is exported."
            )

        return cls(
            sm_arch=sm_arch,
            trt_version=trt_version,
            cuda_version=cuda_version,
        )

    def make_label(self) -> str:
        """Generate the engine label string."""
        return f"{self.sm_arch}_trt-llm-{self.trt_version}_cuda{self.cuda_version}"


# ============================================================================
# Engine Label
# ============================================================================

def get_engine_label(engine_path: Path) -> str:
    """Generate engine label from build metadata or environment variables.

    Args:
        engine_path: Path to TRT-LLM engine directory.

    Returns:
        Engine label string (e.g., "sm90_trt-llm-0.17.0_cuda12.8").

    Raises:
        EngineLabelError: If required values cannot be determined.
    """
    # Try build_metadata.json first - it has the exact values used at build time
    meta_path = engine_path / "build_metadata.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            sm = meta.get("sm_arch")
            trt_ver = meta.get("tensorrt_llm_version")
            cuda_ver = meta.get("cuda_toolkit") or meta.get("cuda_version")

            if sm and trt_ver and cuda_ver:
                return f"{sm}_trt-llm-{trt_ver}_cuda{cuda_ver}"
        except Exception:
            pass

    # Fall back to environment
    env_info = EnvironmentInfo.from_env()
    return env_info.make_label()


__all__ = [
    "EngineLabelError",
    "EnvironmentInfo",
    "get_engine_label",
    "_env_int",
    "_env_str",
]

