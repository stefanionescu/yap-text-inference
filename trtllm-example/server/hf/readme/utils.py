import os
from pathlib import Path
from typing import Any


def safe_get(dct: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = dct or {}
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def template_repo_root() -> Path:
    try:
        # this file is .../server/hf/readme/utils.py -> repo root is parents[3]
        return Path(__file__).resolve().parents[3]
    except Exception:
        return Path.cwd()


def to_link(model_id: str) -> str:
    model_id = (model_id or "").strip()
    if not model_id:
        return "Orpheus 3B"
    return f"[{model_id}](https://huggingface.co/{model_id})"


def render_template(template_text: str, mapping: dict) -> str:
    rendered = template_text
    for k, v in mapping.items():
        rendered = rendered.replace("{{" + k + "}}", str(v))
    return rendered


def source_model_from_env_or_meta(meta: dict) -> str:
    env_model = os.environ.get("MODEL_ID") or ""
    if not env_model:
        preset = (os.environ.get("MODEL_PRESET") or "canopy").strip().lower()
        env_model = "yapwithai/fast-orpheus-3b-0.1-ft" if preset == "fast" else "yapwithai/canopy-orpheus-3b-0.1-ft"
    if env_model:
        return env_model
    from_meta = safe_get(meta, "model_id", default="") or safe_get(meta, "base_model", default="")
    return str(from_meta) if from_meta else "yapwithai/canopy-orpheus-3b-0.1-ft"
