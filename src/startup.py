"""Server startup helpers (logging + warmup orchestration)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any
from collections.abc import Awaitable, Callable

from vllm.sampling_params import SamplingParams

from .config import DEPLOY_CHAT, DEPLOY_TOOL
from .engines import get_chat_engine, get_tool_engine
from .tokens.tokenizer import get_chat_tokenizer, get_tool_tokenizer

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WarmupPlan:
    name: str
    prompt: str
    priority: int
    engine_getter: Callable[[], Awaitable[Any]]


class StartupWarmup:
    """Warm tokenizers and engines before serving traffic."""

    def __init__(self, sampling_params: SamplingParams | None = None, attempts: int = 2):
        self._params = sampling_params or SamplingParams(temperature=0.0, max_tokens=1, stop=["\n", "</s>"])
        self._attempts = max(attempts, 1)

    async def run(self) -> None:
        await self._warm_tokenizers()
        plans = self._build_plans()
        if not plans:
            return
        await asyncio.gather(*(self._warm_engine(plan) for plan in plans))

    async def _warm_tokenizers(self) -> None:
        try:
            if DEPLOY_CHAT:
                get_chat_tokenizer()
            if DEPLOY_TOOL:
                get_tool_tokenizer()
        except Exception as exc:  # noqa: BLE001 - best effort
            logger.warning("startup_warmup: tokenizer warmup failed: %s", exc)

    def _build_plans(self) -> list[WarmupPlan]:
        plans: list[WarmupPlan] = []
        if DEPLOY_CHAT:
            plans.append(
                WarmupPlan(
                    name="chat",
                    prompt="<|persona|>\nWARM\n<|assistant|>\n",
                    priority=0,
                    engine_getter=get_chat_engine,
                )
            )
        if DEPLOY_TOOL:
            plans.append(
                WarmupPlan(
                    name="tool",
                    prompt="warmup",
                    priority=1,
                    engine_getter=get_tool_engine,
                )
            )
        return plans

    async def _warm_engine(self, plan: WarmupPlan) -> None:
        for attempt in range(1, self._attempts + 1):
            try:
                rid = f"warm-{plan.name}-{uuid.uuid4()}"
                engine = await plan.engine_getter()
                stream = engine.generate(
                    prompt=plan.prompt,
                    sampling_params=self._params,
                    request_id=rid,
                    priority=plan.priority,
                )
                async for _ in stream:
                    break
                logger.info("startup_warmup: %s engine ready (attempt=%s)", plan.name, attempt)
                return
            except Exception as exc:  # noqa: BLE001 - best effort
                logger.warning("startup_warmup: %s engine warm attempt %s failed: %s", plan.name, attempt, exc)
                await asyncio.sleep(min(0.5 * attempt, 2.0))

