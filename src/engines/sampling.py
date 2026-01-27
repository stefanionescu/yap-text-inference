"""Unified sampling parameters factory.

Creates engine-specific SamplingParams based on the configured inference engine.

This module abstracts the differences between vLLM and TensorRT-LLM sampling
parameter formats:

vLLM SamplingParams:
    - Uses -1 for disabled top_k
    - Supports logit_bias directly
    - All penalty parameters supported

TensorRT-LLM SamplingParams:
    - Uses None for disabled top_k
    - No logit_bias support (silently ignored)
    - Some penalties may not be supported in all versions

The factory function handles these differences, providing a consistent
interface for callers regardless of the backend engine.
"""

from __future__ import annotations

from typing import Any

from src.config import INFERENCE_ENGINE


def _create_vllm_params(
    *,
    temperature: float,
    top_p: float,
    top_k: int,
    min_p: float,
    repetition_penalty: float,
    presence_penalty: float,
    frequency_penalty: float,
    max_tokens: int,
    stop: list[str] | None,
    logit_bias: dict[int, float] | None,
) -> Any:
    """Create vLLM SamplingParams."""
    from vllm.sampling_params import SamplingParams
    
    return SamplingParams(
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        min_p=min_p,
        repetition_penalty=repetition_penalty,
        presence_penalty=presence_penalty,
        frequency_penalty=frequency_penalty,
        max_tokens=max_tokens,
        stop=stop,
        logit_bias=logit_bias if logit_bias else None,
    )


def _create_trt_params(
    *,
    temperature: float,
    top_p: float,
    top_k: int,
    min_p: float,
    repetition_penalty: float,
    presence_penalty: float,
    frequency_penalty: float,
    max_tokens: int,
    stop: list[str] | None,
) -> Any:
    """Create TensorRT-LLM SamplingParams."""
    from tensorrt_llm import SamplingParams

    # TRT-LLM uses slightly different parameter names/defaults
    kwargs: dict[str, Any] = {
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    
    # top_k: TRT uses None for disabled, vLLM uses -1
    if top_k > 0:
        kwargs["top_k"] = top_k
    
    # These may not be supported by all TRT versions
    if repetition_penalty != 1.0:
        kwargs["repetition_penalty"] = repetition_penalty
    if presence_penalty != 0.0:
        kwargs["presence_penalty"] = presence_penalty
    if frequency_penalty != 0.0:
        kwargs["frequency_penalty"] = frequency_penalty
    if stop:
        kwargs["stop"] = stop
    
    return SamplingParams(**kwargs)


def create_sampling_params(
    *,
    temperature: float = 1.0,
    top_p: float = 1.0,
    top_k: int = -1,
    min_p: float = 0.0,
    repetition_penalty: float = 1.0,
    presence_penalty: float = 0.0,
    frequency_penalty: float = 0.0,
    max_tokens: int = 256,
    stop: list[str] | None = None,
    logit_bias: dict[int, float] | None = None,
) -> Any:
    """Create engine-specific sampling parameters.
    
    Args:
        temperature: Sampling temperature (higher = more random).
        top_p: Nucleus sampling probability threshold.
        top_k: Top-K sampling limit (-1 = disabled).
        min_p: Minimum probability threshold.
        repetition_penalty: Penalty for repeated tokens.
        presence_penalty: Penalty for tokens already present.
        frequency_penalty: Penalty based on token frequency.
        max_tokens: Maximum tokens to generate.
        stop: Stop sequences.
        logit_bias: Token ID to logit bias mapping.
        
    Returns:
        Engine-specific SamplingParams instance.
    """
    if INFERENCE_ENGINE == "vllm":
        return _create_vllm_params(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            min_p=min_p,
            repetition_penalty=repetition_penalty,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            max_tokens=max_tokens,
            stop=stop,
            logit_bias=logit_bias,
        )
    else:
        return _create_trt_params(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            min_p=min_p,
            repetition_penalty=repetition_penalty,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            max_tokens=max_tokens,
            stop=stop,
        )


__all__ = ["create_sampling_params"]

