"""Model-family profiles defining special runtime requirements.

Different model families have unique requirements that can't be determined
from their architecture alone. This module defines profiles that capture:

- Dtype requirements (bfloat16 vs float16)
- Attention backend compatibility (FlashInfer, XFORMERS)
- Memory optimization needs
- Tokenizer fixes
- Custom package dependencies (e.g., fla-core for Kimi models)

Profiles are matched by checking if any marker string appears in the
model identifier (case-insensitive). The first matching profile wins.

Example:
    Model "TheDrummer/gemma-3-27b-it" matches the "gemma3" profile because
    it contains "gemma-3". This profile enables bfloat16 and memory
    optimization.

Adding New Profiles:
    1. Add a new ModelProfile entry to MODEL_PROFILES tuple
    2. Define marker strings that uniquely identify the model family
    3. Set appropriate flags for the model's requirements
    4. More specific profiles should come before generic ones
"""

from __future__ import annotations

from src.state import ModelProfile

MODEL_PROFILES: tuple[ModelProfile, ...] = (
    ModelProfile(
        name="gemma3",
        markers=("gemma-3", "gemma3"),
        requires_bfloat16=True,
        needs_memory_optimization=True,
    ),
    ModelProfile(
        name="gemma2",
        markers=("gemma-2", "gemma2", "gemma-27b", "gemma-9b"),
        requires_bfloat16=True,
        needs_memory_optimization=True,
        # NOTE: Some Gemma2 finetunes have tie_word_embeddings=false which breaks vLLM's
        # assertion but works fine otherwise.
    ),
    ModelProfile(
        name="gemma",
        markers=("gemma",),
        needs_memory_optimization=True,
    ),
    ModelProfile(
        name="kimi-linear",
        markers=("kimi-linear", "kimi_linear"),
        requires_bfloat16=True,
        requires_fla_runtime=True,
    ),
    ModelProfile(
        name="kimi",
        markers=("kimi",),
        requires_fla_runtime=True,
    ),
    # DeepSeek-V2/V3 models use MLA (Multi-Head Latent Attention)
    # FLASHINFER doesn't support MLA, so we need to unset the backend to allow auto-selection
    ModelProfile(
        name="deepseek-v2",
        markers=("deepseek-v2", "deepseek_v2", "deepseekcoder-v2", "deepseek-v3", "deepseek_v3"),
        uses_mla=True,
    ),
    # Moonlight uses DeepSeek V3 architecture with MLA (Multi-Head Latent Attention)
    # FLASHINFER doesn't support MLA, so we need to unset the backend to allow auto-selection
    ModelProfile(
        name="moonlight",
        markers=("moonlight",),
        requires_bfloat16=True,
        uses_mla=True,
    ),
    # Qwen3-Next uses hybrid DeltaNet + Attention architecture
    # It requires bfloat16 to avoid dtype mismatches in torch.compile
    # Must come before generic qwen3 profile to match first
    ModelProfile(
        name="qwen3-next",
        markers=("qwen3-next", "qwen3_next"),
        requires_bfloat16=True,
        tokenizer_kwargs={"fix_mistral_regex": True},
    ),
    ModelProfile(
        name="qwen3",
        markers=("qwen3",),
        tokenizer_kwargs={"fix_mistral_regex": True},
    ),
    # Mistral Small 3.x models have a broken tokenizer regex pattern
    # See: https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503/discussions/84
    ModelProfile(
        name="mistral-small-3",
        markers=("mistral-small-3",),
        tokenizer_kwargs={"fix_mistral_regex": True},
    ),
)


__all__ = [
    "MODEL_PROFILES",
    "ModelProfile",
]
