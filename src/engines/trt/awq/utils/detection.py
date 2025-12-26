"""Runtime detection utilities for TRT-LLM builds."""

from __future__ import annotations

import subprocess


def detect_tensorrt_llm_version() -> str:
    """Detect TensorRT-LLM version at runtime."""
    try:
        import tensorrt_llm
        return tensorrt_llm.__version__
    except Exception:
        return "unknown"


def detect_cuda_version() -> str:
    """Detect CUDA version at runtime."""
    try:
        result = subprocess.run(
            ["nvcc", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Parse "release X.Y" from output
        for line in result.stdout.split("\n"):
            if "release" in line.lower():
                parts = line.split("release")
                if len(parts) > 1:
                    version = parts[1].split(",")[0].strip()
                    return version
    except Exception:
        pass
    return "unknown"


def detect_gpu_name() -> str:
    """Detect GPU name at runtime."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip().split("\n")[0] or "unknown"
    except Exception:
        return "unknown"


# SM architecture to compute capability mapping
SM_COMPUTE_CAPABILITY: dict[str, tuple[str, str]] = {
    "sm89": ("8.9", "Ada Lovelace / RTX 40 series"),
    "sm90": ("9.0", "Hopper / H100"),
    "sm100": ("10.0", "Blackwell / B200"),
}


def get_compute_capability_info(sm_arch: str) -> dict[str, str]:
    """Derive compute capability info from SM architecture.
    
    Args:
        sm_arch: SM architecture string (e.g., "sm90").
        
    Returns:
        Dict with 'min_compute_capability' and 'gpu_arch_note'.
    """
    # Extract numeric part from sm_arch (e.g., "sm90" -> "90")
    sm_num = sm_arch.replace("sm", "") if sm_arch.startswith("sm") else sm_arch
    sm_key = f"sm{sm_num}"
    
    if sm_key in SM_COMPUTE_CAPABILITY:
        cc, note = SM_COMPUTE_CAPABILITY[sm_key]
        return {"min_compute_capability": cc, "gpu_arch_note": note}
    
    # Default fallback
    return {"min_compute_capability": "8.9", "gpu_arch_note": "Ada Lovelace+"}

