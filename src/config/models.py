"""Model allowlists and validation helpers, including AWQ support."""

import os

from .env import QUANTIZATION


ALLOWED_CHAT_MODELS: list[str] = [
    # Full precision models
    "kyx0r/Neona-12B", # decent but hallucinates stuff when you say you wanna use an app/see the screen, gotta filter emojis and tell it to stop explaining itself
    "Epiculous/Violet_Twilight-v0.2", # weird personality and hard to steer
    "SicariusSicariiStuff/Impish_Nemo_12B", # unstable once it gets past 0.8 temp, not like the model card describes it
    "SicariusSicariiStuff/Wingless_Imp_8B",
    "SicariusSicariiStuff/Impish_Mind_8B",
    "SicariusSicariiStuff/Eximius_Persona_5B",
    "SicariusSicariiStuff/Impish_LLAMA_4B",
    "SicariusSicariiStuff/Fiendish_LLAMA_3B",
    "TheDrummer/Cydonia-Redux-22B-v1.1", # unintelligible/stupid 
    "TheDrummer/Cydonia-24B-v4.1", # sassy/pessimistic, hard to steer
    "TheDrummer/Skyfall-31B-v4", # stupid even at lower temperatures
    "TheDrummer/Skyfall-36B-v2", # might be decent but gotta have a super strong system prompt
    "dphn/Dolphin-Mistral-24B-Venice-Edition", # stupid, repetitive, ignores instructions at 4bit. did not test 8bit, it's too big for L40S
    "dphn/dolphin-2.9.3-mistral-nemo-12b", # adds random characters at the beginning of the response and uses 3rd person to describe itself
    "FallenMerick/MN-Violet-Lotus-12B", # stupid and hallucinates a ton
    "ReadyArt/Broken-Tutu-24B-Unslop-v2.0", # I like the reply length/chatty format but it just ignores instructions or maybe the prompt needs to be massaged
    "mistralai/Mixtral-8x7B-v0.1", # good assistant, useless for RP
    "mistralai/Mixtral-8x7B-Instruct-v0.1", # suprisingly dumb
    "TheDrummer/Magidonia-24B-v4.2.0", # weird personality, not flirty even when I tell it to be like that
    "TheDrummer/Snowpiercer-15B-v3", # kinda stupid and horrible at temp > 0.6
    "TheDrummer/Theia-21B-v2", # I'm shocked and really impressed, might be a good model
    "concedo/Beepo-22B", # stupid
    "zetasepic/Qwen2.5-32B-Instruct-abliterated-v2", # unintelligible and dumb
    "OddTheGreat/Mechanism_24B_V.1", # yaps too much and is sorta unstable at high temp
    "zai-org/glm-4-9b-chat-hf", # BROKEN: might get back later
    "zai-org/GLM-4-32B-Base-0414", # BROKEN: not supported by AutoAWQ
    "zai-org/GLM-4-32B-0414", # BROKEN: not supported by AutoAWQ
    "Doctor-Shotgun/MS3.2-24B-Magnum-Diamond", # Actually pretty good, gotta iron out some details tho
    "EVA-UNIT-01/EVA-Qwen2.5-32B-v0.1", # has its moments of genius but generally silly/doesn't stick to the sys prompt
    "allura-org/Qwen2.5-32b-RP-Ink", # REALLY good but yaps too much, might wanna use a length penalty or a really tight prompt
    "PocketDoc/Dans-PersonalityEngine-V1.3.0-24b", # crap that hallucinates even at 0.6 temp
    # Pre-quantized GPTQ models
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128",
    "SicariusSicariiStuff/Impish_Magic_24B_GPTQ_4-bit-32",
    "SicariusSicariiStuff/Fiendish_LLAMA_3B_GPTQ-4-bit-128",
    # Pre-quantized AWQ models
    "yapwithai/impish-12b-awq",
]

ALLOWED_TOOL_MODELS: list[str] = [
    # Full precision models
    "MadeAgents/Hammer2.1-1.5b",
    "MadeAgents/Hammer2.1-3b",
    # Pre-quantized AWQ models
    "yapwithai/hammer-2.1-3b-awq",
]


def _is_local_model_path(value: str | None) -> bool:
    if not value:
        return False
    try:
        return os.path.exists(value)
    except Exception:
        return False


def _is_awq_model(value: str | None) -> bool:
    """Check if model name suggests it's a pre-quantized AWQ model."""
    if not value:
        return False
    return "awq" in value.lower() and "/" in value


def is_valid_model(model: str, allowed_models: list, model_type: str) -> bool:
    """Enhanced model validation with AWQ support."""
    if not model:
        return False

    # Check if it's in the explicit allowed list
    if model in allowed_models:
        return True

    # Check if it's a local path
    if _is_local_model_path(model):
        return True

    # For AWQ quantization, be more permissive with AWQ model names
    if QUANTIZATION == "awq" and _is_awq_model(model):
        return True

    return False


__all__ = [
    "ALLOWED_CHAT_MODELS",
    "ALLOWED_TOOL_MODELS",
    "_is_local_model_path",
    "_is_awq_model",
    "is_valid_model",
]


