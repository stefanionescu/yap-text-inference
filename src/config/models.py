"""Model allowlists for chat and tool deployment.

This module contains the approved model lists for the inference stack:

Chat Models (ALLOWED_BASE_CHAT_MODELS):
    Base HuggingFace models that can be quantized for chat. Includes notes
    on quality, temperature stability, and use cases from testing.

MoE Chat Models (ALLOWED_BASE_MOE_CHAT_MODELS):
    Mixture of Experts models requiring special quantization handling.
    These use sparse activation and have different memory profiles.

Pre-Quantized Models:
    - ALLOWED_VLLM_QUANT_CHAT_MODELS: AWQ/GPTQ models ready for vLLM
    - ALLOWED_TRT_QUANT_CHAT_MODELS: AWQ/FP8 models built for TRT-LLM

Tool Models (ALLOWED_TOOL_MODELS):
    Classifier models for screenshot intent detection. These use
    transformers AutoModelForSequenceClassification, not vLLM.

Adding New Models:
    1. Test the model thoroughly before adding
    2. Include a comment with notes on quality/stability
    3. Add to the appropriate list based on architecture
"""

ALLOWED_BASE_CHAT_MODELS: list[str] = [
    "SicariusSicariiStuff/Impish_Nemo_12B", # unstable above 0.8 temp when using 4bit quant; decent <=0.6
    "TheDrummer/Theia-21B-v2", # mid intelligence; ok for cheaper long runs
    "TheDrummer/Rocinante-12B-v1.1", # mid intelligence; downgrade option, weak on instruction following
    "knifeayumu/Cydonia-v1.3-Magnum-v4-22B", # pretty bad overall
    "Doctor-Shotgun/MS3.2-24B-Magnum-Diamond",
    "anthracite-org/magnum-v2-32b", # a bit cheesy and yaps too much (good for general RP tho)
    "djuna/magnum-v2-32b-chatml", # yaps too much but might fix with prompting (good for general RP tho)
    "zerofata/MS3.2-PaintedFantasy-Visage-33B", # better than Cydonia but still quirky
    "anthracite-org/magnum-v4-72b", # amazing on OpenRouter but too big
    "anthracite-org/magnum-v1-72b", # amazing on OpenRouter but too big
    "dphn/Dolphin3.0-Llama3.1-8B",
    "ArliAI/DS-R1-Qwen3-8B-ArliAI-RpR-v4-Small",
    "nvidia/Llama-3_1-Nemotron-51B-Instruct",
    "mistralai/Ministral-8B-Instruct-2410",
    "zerofata/L3.3-GeneticLemonade-Unleashed-v3-70B",
    "chargoddard/storytime-13b",
    "Qwen/Qwen3-14B",
    "soob3123/GrayLine-Qwen3-14B",
    "Jinx-org/Jinx-Qwen3-32B",
    "Jinx-org/Jinx-Qwen3-14B",
    "deepseek-ai/DeepSeek-V2-Lite-Chat",
    "mistralai/Mistral-Nemo-Instruct-2407",
    "SteelStorage/L3-Aethora-15B-V2",
    "Delta-Vector/Ohashi-NeMo-12B",
    "concedo/Beepo-22B",
    "Gryphe/Pantheon-RP-Pure-1.6.2-22b-Small",
    "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
    "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
    "mistralai/Mistral-Small-24B-Instruct-2501",
    "Gryphe/Pantheon-RP-1.6.2-22b-Small",
    "Gryphe/Pantheon-RP-1.8-24b-Small-3.1",
    "mistralai/Magistral-Small-2509",
    "TheDrummer/UnslopNemo-12B-v4.1", # PRETTY GOOD: needs more testing tho
    "SicariusSicariiStuff/Impish_Bloodmoon_12B",
    "SicariusSicariiStuff/Angelic_Eclipse_12B",
    "flammenai/Mahou-1.3-mistral-nemo-12B",
    "Qwen/Qwen3-32B",
    "mistralai/Mistral-Small-Instruct-2409",
    "ReadyArt/Broken-Tutu-24B-Unslop-v2.0",
    "Delta-Vector/Rei-24B-KTO",
    "ArliAI/Qwen2.5-32B-ArliAI-RPMax-v1.3",
    "ArliAI/Mistral-Small-22B-ArliAI-RPMax-v1.1",
    "ArliAI/Mistral-Small-24B-ArliAI-RPMax-v1.4",
    "Naphula/Goetia-24B-v1.1",
    "Mawdistical/Squelching-Fantasies-qw3-14B",
    "Qwen/QwQ-32B",
    "dphn/Dolphin-Mistral-24B-Venice-Edition",
    "ReadyArt/Broken-Tutu-24B-Transgression-v2.0",
    "mistralai/Ministral-3-14B-Instruct-2512",
    "TheDrummer/Magidonia-24B-v4.3",
]

ALLOWED_BASE_MOE_CHAT_MODELS: list[str] = [
    "Qwen/Qwen3-30B-A3B-Instruct-2507",
    "ArliAI/Qwen3-30B-A3B-ArliAI-RpR-v4-Fast",
    "DavidAU/Qwen3-33B-A3B-Stranger-Thoughts-IPONDER",
    "Ewere/Qwen3-30B-A3B-abliterated-erotic",
    "Qwen/Qwen3-Next-80B-A3B-Instruct",
    "baidu/ERNIE-4.5-21B-A3B-PT",
    "moonshotai/Moonlight-16B-A3B-Instruct",
    "kakaocorp/kanana-1.5-15.7b-a3b-instruct",
    "moonshotai/Kimi-Linear-48B-A3B-Instruct",
    "cerebras/Kimi-Linear-REAP-35B-A3B-Instruct",
    "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    "bgg1996/Melinoe-30B-A3B-Thinking",
]

ALLOWED_VLLM_QUANT_CHAT_MODELS: list[str] = [
    # Pre-quantized GPTQ models
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64",
    "SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128",

    # Pre-quantized AWQ/W4A16/NVFP4 models
    "RedHatAI/Mistral-Small-3.1-24B-Instruct-2503-quantized.w4a16",
    "leon-se/gemma-3-27b-it-qat-W4A16-G128",
    "cyankiwi/Kimi-Linear-48B-A3B-Instruct-AWQ-4bit",
    "NaomiBTW/Cydonia-v1.3-Magnum-v4-22B-AWQ", # stupid and random as fuck
    "TheBloke/30B-Lazarus-AWQ", # completely ignores instructions, super dumb
    "cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit", # GOOD but lots of GPT-isms
    "Qwen/Qwen3-32B-AWQ",
    "Qwen/Qwen3-14B-AWQ",
    "warshanks/Ministral-8B-Instruct-2410-AWQ",
    "TheBloke/mixtral-8x7b-v0.1-AWQ",
    "casperhansen/mistral-nemo-instruct-2407-awq",
    "cpatonn/Llama-3_3-Nemotron-Super-49B-v1_5-AWQ-4bit",
    "jeffcookio/Mistral-Small-3.2-24B-Instruct-2506-awq-sym", # BEST CHAT MODEL FOR NOW

    "yapwithai/arliai-qwen3-30B-a3b-arliai-rpr-v4-fast-w4a16",
    "yapwithai/bgg1996-melinoe-30B-A3B-thinking-w4a16",
]

ALLOWED_TRT_QUANT_CHAT_MODELS: list[str] = [
    # Pre-quantized AWQ/W4A16 models
    "yapwithai/readyart-broken-tutu-24B-transgression-v2.0-trt-awq", # LOVE the initial reactions, gotta test more
]

ALLOWED_TOOL_MODELS: list[str] = [
    "yapwithai/yap-longformer-screenshot-intent",
    "yapwithai/yap-modernbert-screenshot-intent"
]

__all__ = [
    "ALLOWED_BASE_CHAT_MODELS",
    "ALLOWED_BASE_MOE_CHAT_MODELS",
    "ALLOWED_VLLM_QUANT_CHAT_MODELS",
    "ALLOWED_TRT_QUANT_CHAT_MODELS",
    "ALLOWED_TOOL_MODELS",
]
