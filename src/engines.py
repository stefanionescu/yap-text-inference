"""Engine management for vLLM chat and tool models."""

from __future__ import annotations

import os
import asyncio
import logging
import subprocess
from typing import Tuple, Dict, Optional

# Ensure V1 engine path before importing vLLM
os.environ.setdefault("VLLM_USE_V1", "1")

from vllm.engine.async_llm_engine import AsyncLLMEngine

from .config import (
    CHAT_GPU_FRAC,
    CHAT_MAX_LEN,
    CHAT_MODEL,
    TOOL_MODEL,
    TOOL_GPU_FRAC,
    TOOL_MAX_LEN,
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    QUANTIZATION,
    KV_DTYPE,
    MAX_CONCURRENT_CONNECTIONS,
    MAX_USERS_WITH_TOOLCALLS,
    make_engine_args,
)


_chat_engine: AsyncLLMEngine | None = None
_tool_engine: AsyncLLMEngine | None = None

# Lock to prevent concurrent engine construction (but not generation)
_ENGINE_CONSTRUCTION_LOCK = asyncio.Lock()


def _build_engines() -> Tuple[AsyncLLMEngine | None, AsyncLLMEngine | None]:
    """Build engines with reduced logging and summary at end."""
    logger = logging.getLogger(__name__)
    
    # Temporarily suppress vLLM's verbose logging during construction
    vllm_logger = logging.getLogger("vllm")
    original_level = vllm_logger.level
    vllm_logger.setLevel(logging.WARNING)
    
    try:
        tool = None
        chat = None
        
        if DEPLOY_TOOL:
            logger.info(f"Loading tool model: {TOOL_MODEL}")
            tool = AsyncLLMEngine.from_engine_args(
                make_engine_args(TOOL_MODEL, TOOL_GPU_FRAC, TOOL_MAX_LEN, is_chat=False)
            )
        
        if DEPLOY_CHAT:
            logger.info(f"Loading chat model: {CHAT_MODEL}")
            chat = AsyncLLMEngine.from_engine_args(
                make_engine_args(CHAT_MODEL, CHAT_GPU_FRAC, CHAT_MAX_LEN, is_chat=True)
            )
        
        # Log deployment summary
        _log_deployment_summary(chat, tool)
        
        return chat, tool
    
    finally:
        # Restore original vLLM logging level
        vllm_logger.setLevel(original_level)


def _get_gpu_memory_info() -> Dict[str, float]:
    """Get GPU memory information in GB."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.total,memory.used,memory.free', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            total_mb, used_mb, free_mb = map(float, result.stdout.strip().split(','))
            return {
                'total_gb': total_mb / 1024,
                'used_gb': used_mb / 1024,
                'free_gb': free_mb / 1024
            }
    except Exception:
        pass
    return {'total_gb': 0.0, 'used_gb': 0.0, 'free_gb': 0.0}


def _estimate_model_memory_gb(model_name: str, quantization: str) -> float:
    """Estimate model weight memory usage in GB."""
    # Model parameter estimates (in billions)
    param_counts = {
        'Impish_Nemo_12B': 12.0, 'Impish_Magic_24B': 24.0, 'Wingless_Imp_8B': 8.0,
        'Impish_Mind_8B': 8.0, 'Neona-12B': 12.0, 'SOLAR-10.7B': 10.7,
        'Eximius_Persona_5B': 5.0, 'Impish_LLAMA_4B': 4.0, 'Fiendish_LLAMA_3B': 3.0,
        'Hammer2.1-1.5b': 1.5, 'Hammer2.1-3b': 3.0
    }
    
    # Find matching model size
    params = 12.0  # default fallback
    for key, size in param_counts.items():
        if key in model_name:
            params = size
            break
    
    # Memory usage by quantization
    if 'gptq' in quantization.lower():
        bytes_per_param = 0.5  # 4-bit
    elif quantization == 'fp8':
        bytes_per_param = 1.0  # 8-bit
    else:
        bytes_per_param = 2.0  # fp16 fallback
    
    return params * bytes_per_param


def _estimate_kv_memory_per_user_gb(model_name: str, max_len: int, kv_dtype: str) -> float:
    """Estimate KV cache memory per concurrent user in GB."""
    # Model architecture estimates (layers, hidden_size)
    arch_info = {
        'Impish_Nemo_12B': (40, 5120), 'Impish_Magic_24B': (48, 6144), 'Wingless_Imp_8B': (32, 4096),
        'Impish_Mind_8B': (32, 4096), 'Neona-12B': (40, 5120), 'SOLAR-10.7B': (32, 4096),
        'Eximius_Persona_5B': (32, 4096), 'Impish_LLAMA_4B': (32, 4096), 'Fiendish_LLAMA_3B': (26, 3200),
        'Hammer2.1-1.5b': (24, 2048), 'Hammer2.1-3b': (32, 2560)
    }
    
    # Find matching architecture
    layers, hidden_size = 40, 5120  # default
    for key, (l, h) in arch_info.items():
        if key in model_name:
            layers, hidden_size = l, h
            break
    
    # KV dtype sizes
    kv_dtype_lower = kv_dtype.lower()
    if 'fp8' in kv_dtype_lower:
        dtype_bytes = 1
    elif 'int8' in kv_dtype_lower:
        dtype_bytes = 1
    else:  # fp16/auto
        dtype_bytes = 2
    
    # KV cache: seq_len * hidden_size * layers * 2 (K+V) * dtype_bytes
    kv_bytes_per_seq = max_len * hidden_size * layers * 2 * dtype_bytes
    return kv_bytes_per_seq / (1024**3)  # Convert to GB


def _calculate_concurrent_capacity(gpu_info: Dict[str, float]) -> Dict[str, int]:
    """Calculate actual concurrent user capacity based on available GPU memory."""
    available_memory_gb = gpu_info['free_gb']
    
    # Estimate memory usage for deployed models
    total_model_memory = 0.0
    total_kv_memory_per_user = 0.0
    
    if DEPLOY_CHAT:
        chat_model_memory = _estimate_model_memory_gb(CHAT_MODEL or '', QUANTIZATION)
        chat_kv_per_user = _estimate_kv_memory_per_user_gb(CHAT_MODEL or '', CHAT_MAX_LEN, KV_DTYPE)
        total_model_memory += chat_model_memory * CHAT_GPU_FRAC
        total_kv_memory_per_user += chat_kv_per_user
    
    if DEPLOY_TOOL:
        tool_model_memory = _estimate_model_memory_gb(TOOL_MODEL or '', 'fp16')  # Tool models unquantized
        tool_kv_per_user = _estimate_kv_memory_per_user_gb(TOOL_MODEL or '', TOOL_MAX_LEN, KV_DTYPE)
        total_model_memory += tool_model_memory * TOOL_GPU_FRAC
        total_kv_memory_per_user += tool_kv_per_user
    
    # Available memory for KV cache (after model weights + safety margin)
    safety_margin_gb = 0.5
    available_for_kv = max(0, available_memory_gb - total_model_memory - safety_margin_gb)
    
    # Calculate concurrent users
    if total_kv_memory_per_user > 0:
        memory_limited_users = int(available_for_kv / total_kv_memory_per_user)
    else:
        memory_limited_users = 0
    
    return {
        'memory_limited': memory_limited_users,
        'connection_limited': MAX_CONCURRENT_CONNECTIONS,
        'effective_capacity': min(memory_limited_users, MAX_CONCURRENT_CONNECTIONS) if memory_limited_users > 0 else MAX_CONCURRENT_CONNECTIONS
    }


def _log_deployment_summary(chat_engine: AsyncLLMEngine | None, tool_engine: AsyncLLMEngine | None) -> None:
    """Log a summary of deployed models and their capacities."""
    logger = logging.getLogger(__name__)
    
    deployed = []
    if chat_engine:
        deployed.append(f"Chat: {CHAT_MODEL} ({CHAT_GPU_FRAC:.0%} GPU)")
    if tool_engine:
        deployed.append(f"Tool: {TOOL_MODEL} ({TOOL_GPU_FRAC:.0%} GPU)")
    
    logger.info("=" * 60)
    logger.info(f"Deployment ready: {', '.join(deployed)}")
    
    # Get GPU memory information and calculate capacity
    gpu_info = _get_gpu_memory_info()
    capacity = _calculate_concurrent_capacity(gpu_info)
    
    # Log memory analysis
    if gpu_info['total_gb'] > 0:
        logger.info(f"GPU Memory: {gpu_info['total_gb']:.1f}GB total, {gpu_info['used_gb']:.1f}GB used, {gpu_info['free_gb']:.1f}GB free")
    
    # Log engine configuration details
    concurrent_mode = os.getenv("CONCURRENT_MODEL_CALL", "1") == "1"
    concurrent_status = "CONCURRENT" if concurrent_mode else "SEQUENTIAL"
    logger.info(f"Model execution mode: {concurrent_status}")
    
    # Log actual concurrent user capacity
    logger.info(f"Concurrent user capacity:")
    if capacity['memory_limited'] > 0:
        logger.info(f"  Memory-limited: {capacity['memory_limited']} users (based on KV cache)")
        logger.info(f"  Connection-limited: {capacity['connection_limited']} users (connection pool)")
        logger.info(f"  Effective capacity: {capacity['effective_capacity']} concurrent users")
    else:
        logger.info(f"  Connection-limited: {capacity['connection_limited']} users (memory calc unavailable)")
    
    # Log per-model configuration
    if chat_engine:
        chat_kv_gb = _estimate_kv_memory_per_user_gb(CHAT_MODEL or '', CHAT_MAX_LEN, KV_DTYPE)
        logger.info(f"Chat model: max_len={CHAT_MAX_LEN}, KV={chat_kv_gb:.2f}GB/user")
    if tool_engine:
        tool_kv_gb = _estimate_kv_memory_per_user_gb(TOOL_MODEL or '', TOOL_MAX_LEN, KV_DTYPE)
        logger.info(f"Tool model: max_len={TOOL_MAX_LEN}, KV={tool_kv_gb:.2f}GB/user")
    
    # Log chunked prefill status
    chunked_prefill_enabled = "gptq" not in QUANTIZATION.lower()
    prefill_status = "ENABLED" if chunked_prefill_enabled else "DISABLED (GPTQ detected)"
    logger.info(f"Chunked prefill: {prefill_status}")
    
    # Log quantization and KV info
    logger.info(f"Quantization: {QUANTIZATION}, KV dtype: {KV_DTYPE}")
    if chunked_prefill_enabled:
        chat_batch = os.getenv("MAX_NUM_BATCHED_TOKENS_CHAT", "512")
        tool_batch = os.getenv("MAX_NUM_BATCHED_TOKENS_TOOL", "256")
        logger.info(f"Max batched tokens: Chat={chat_batch}, Tool={tool_batch}")
    
    # Try to get additional engine info if available
    try:
        if chat_engine and hasattr(chat_engine, 'engine'):
            logger.info("Chat engine ready for inference")
        if tool_engine and hasattr(tool_engine, 'engine'):
            logger.info("Tool engine ready for inference")
    except Exception:
        pass  # Don't fail on stats access
    
    logger.info("=" * 60)


async def get_chat_engine() -> AsyncLLMEngine:
    global _chat_engine, _tool_engine
    if _chat_engine is None or (_tool_engine is None and DEPLOY_TOOL):
        async with _ENGINE_CONSTRUCTION_LOCK:
            # Double-check pattern to avoid building engines twice
            if _chat_engine is None or (_tool_engine is None and DEPLOY_TOOL):
                _chat, _tool = _build_engines()
                _chat_engine, _tool_engine = _chat, _tool
    return _chat_engine  # type: ignore[return-value]


async def get_tool_engine() -> AsyncLLMEngine:
    global _chat_engine, _tool_engine
    if (_chat_engine is None and DEPLOY_CHAT) or _tool_engine is None:
        async with _ENGINE_CONSTRUCTION_LOCK:
            # Double-check pattern to avoid building engines twice
            if (_chat_engine is None and DEPLOY_CHAT) or _tool_engine is None:
                _chat, _tool = _build_engines()
                _chat_engine, _tool_engine = _chat, _tool
    return _tool_engine  # type: ignore[return-value]


