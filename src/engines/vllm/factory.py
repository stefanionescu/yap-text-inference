"""vLLM engine factory."""

from __future__ import annotations

import logging

from src.helpers.env import env_flag
from src.config import CHAT_MODEL, DEPLOY_CHAT, CHAT_MAX_LEN, CHAT_GPU_FRAC

from .engine import VLLMEngine
from .create import create_engine
from .args import make_engine_args
from .setup import configure_runtime_env

logger = logging.getLogger(__name__)


def _create_raw_engine(engine_args: object) -> object:
    """Create the vLLM AsyncLLMEngine with optional log suppression."""
    show_vllm_logs = env_flag("SHOW_VLLM_LOGS", False)

    if show_vllm_logs:
        return create_engine(engine_args)

    from src.scripts.filters.vllm import SuppressedFDContext  # noqa: PLC0415

    with SuppressedFDContext(suppress_stdout=True, suppress_stderr=True):
        return create_engine(engine_args)


async def create_vllm_engine() -> VLLMEngine:
    """Create and validate the vLLM chat engine eagerly."""
    if not DEPLOY_CHAT:
        raise RuntimeError("Chat engine requested but DEPLOY_CHAT=0")
    if not CHAT_MODEL:
        raise RuntimeError("CHAT_MODEL is not configured; cannot start chat engine")

    configure_runtime_env()

    logger.info("vLLM: building chat engine (model=%s)", CHAT_MODEL)
    engine_args = make_engine_args(CHAT_MODEL, CHAT_GPU_FRAC, CHAT_MAX_LEN)
    raw_engine = _create_raw_engine(engine_args)
    engine = VLLMEngine(raw_engine)
    logger.info("vLLM: chat engine ready")
    return engine


__all__ = ["create_vllm_engine"]
