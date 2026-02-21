"""Quantization-related state dataclasses."""

from __future__ import annotations

import os
from src.errors import EngineLabelError
from dataclasses import field, dataclass
from src.config.calibration import CALIB_DEFAULT_DATASET
from src.quantization.trt.detection import detect_gpu_name, detect_cuda_version, detect_tensorrt_llm_version


@dataclass
class CalibrationConfig:
    """Configuration for AWQ calibration."""

    dataset: str = CALIB_DEFAULT_DATASET
    nsamples: int = 64
    seqlen: int = 2048
    w_bit: int = 4
    q_group_size: int = 128
    zero_point: bool = True
    version: str = "GEMM"


@dataclass
class _DatasetInfo:
    requested: str
    effective: str
    fallback_from: str | None = None


@dataclass
class EnvironmentInfo:
    """Container for environment-detected build information."""

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
                "TRT_VERSION not set and tensorrt_llm not importable. This should be set in scripts/lib/env/trt.sh."
            )

        cuda_version = os.getenv("CUDA_VERSION") or detect_cuda_version()
        if not cuda_version or cuda_version == "unknown":
            raise EngineLabelError(
                "CUDA_VERSION not set and nvcc not found. Ensure CUDA is installed or CUDA_VERSION is exported."
            )

        return cls(
            sm_arch=sm_arch,
            trt_version=trt_version,
            cuda_version=cuda_version,
        )

    def make_label(self) -> str:
        """Generate the engine label string."""
        return f"{self.sm_arch}_trt-llm-{self.trt_version}_cuda{self.cuda_version}"


__all__ = [
    "CalibrationConfig",
    "EnvironmentInfo",
    "_DatasetInfo",
]
