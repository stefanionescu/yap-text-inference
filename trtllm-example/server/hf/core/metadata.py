import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

try:
    import torch
except Exception:  # pragma: no cover
    torch = None  # noqa: N816


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _nvidia_smi_row() -> list[str]:
    try:
        cmd = shutil.which("nvidia-smi")
        if not cmd:
            return []
        # nosec - sys utility query; arguments are static
        smi = subprocess.run(  # noqa: S603
            [
                cmd,
                "--query-gpu=name,driver_version,compute_cap",
                "--format=csv,noheader",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        line = (smi.stdout or "").splitlines()[0].strip() if smi.stdout else ""
        return [p.strip() for p in line.split(",")] if line else []
    except Exception:
        return []


def _nvidia_total_vram_gb() -> str:
    """Return total VRAM in GB (integer string) using nvidia-smi, or empty string."""
    try:
        cmd = shutil.which("nvidia-smi")
        if not cmd:
            return ""
        smi = subprocess.run(  # noqa: S603
            [
                cmd,
                "--query-gpu=memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        # memory.total outputs in MiB without units due to nounits; convert to GB (round)
        line = (smi.stdout or "").splitlines()[0].strip() if smi.stdout else ""
        if not line:
            return ""
        mib = float(line)
        gb = int(round(mib / 1024.0))
        return str(gb)
    except Exception:
        return ""


def detect_engine_label(engine_dir: Path, default_label: str | None) -> str:
    """Infer a human-friendly engine label from build metadata or fallback."""
    if default_label:
        return default_label
    data = _read_json(engine_dir / "build_metadata.json")
    sm = data.get("sm_arch") or "smxx"
    trtllm = data.get("tensorrt_llm_version") or ""
    cuda = (data.get("cuda_toolkit") or "").replace(".", "")
    if trtllm and cuda:
        return f"{sm}_trt-llm-{trtllm}_cuda{data.get('cuda_toolkit')}"
    return sm or "engine"


def collect_env_metadata(engine_dir: Path) -> dict:
    """Collect build/runtime metadata to embed in README and uploads."""
    data = _read_json(engine_dir / "build_metadata.json")

    # Runtime info
    data.setdefault("platform", platform.platform())

    build_image = os.environ.get("BUILD_IMAGE")
    if build_image:
        data.setdefault("build_image", build_image)

    trtllm_repo = os.environ.get("TRTLLM_REPO_URL")
    if trtllm_repo:
        data.setdefault("tensorrt_llm_repo", trtllm_repo)

    if torch is not None:
        data.setdefault("torch_version", getattr(torch, "__version__", ""))
        import contextlib

        with contextlib.suppress(Exception):
            data.setdefault("torch_cuda", getattr(torch.version, "cuda", ""))

    row = _nvidia_smi_row()
    min_fields = 3
    if len(row) >= min_fields:
        data.setdefault("gpu_name", row[0])
        data.setdefault("nvidia_driver", row[1])
        data.setdefault("compute_capability", row[2])
    # GPU VRAM (GB)
    vram_gb = _nvidia_total_vram_gb()
    if vram_gb:
        data.setdefault("gpu_vram_gb", vram_gb)

    return data


def _sanitize_slug(text: str) -> str:
    """Lowercase, keep alnum and dashes, convert spaces/underscores to dashes."""
    import re

    t = (text or "").lower()
    t = t.replace("_", "-").replace(" ", "-")
    t = re.sub(r"[^a-z0-9\-]", "", t)
    t = re.sub(r"-{2,}", "-", t).strip("-")
    return t


def derive_hardware_labels(meta: dict) -> tuple[str, str]:
    """Return (slug, pretty) for the GPU hardware.

    Slug examples: a100, h100, l40s, l40, sm80 (fallback)
    Pretty examples: A100, H100, L40S, L40, SM80
    """
    name = (meta.get("gpu_name") or "").lower()
    sm = (meta.get("sm_arch") or "").lower()

    def _from_sm(sm_arch: str) -> tuple[str, str]:
        if "sm80" in sm_arch:
            return "sm80", "SM80"
        if "sm89" in sm_arch:
            return "sm89", "SM89"
        if "sm90" in sm_arch:
            return "sm90", "SM90"
        return (_sanitize_slug(sm_arch) or "smxx", (sm_arch or "SMXX").upper())

    if name:
        if "l40s" in name:
            return "l40s", "L40S"
        if "l40" in name:
            return "l40", "L40"
        if "a100" in name:
            return "a100", "A100"
        if "h100" in name:
            return "h100", "H100"
    # Fallback to SM arch if explicit family not found
    return _from_sm(sm)
