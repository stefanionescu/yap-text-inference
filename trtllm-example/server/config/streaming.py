import os
from dataclasses import dataclass


@dataclass(frozen=True)
class StreamingSettings:
    """TRT-LLM streaming defaults and stop-token policy."""

    # TTS / Streaming (1162 tokens ≈ 14 seconds of audio)
    orpheus_max_tokens: int = int(os.getenv("ORPHEUS_MAX_TOKENS", "1162"))

    # Default sampling parameters used when client omits values
    default_temperature: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.55"))
    default_top_p: float = float(os.getenv("DEFAULT_TOP_P", "0.95"))
    default_repetition_penalty: float = float(os.getenv("DEFAULT_REPETITION_PENALTY", "1.15"))

    # Stop-token policy for the server-side SamplingParams (non-streaming path)
    server_stop_token_ids: tuple[int, ...] = (128009, 128260)

    # TRT-LLM streaming SamplingParams policy (identical behavior centralized)
    trt_detokenize: bool = False
    trt_skip_special_tokens: bool = False
    trt_add_special_tokens: bool = False
    trt_ignore_eos: bool = False
    streaming_stop_token_ids: tuple[int, ...] = (128258, 128262, 128009)  # EOS(speech), EOA, EOT
    streaming_default_max_tokens: int = int(os.getenv("STREAMING_DEFAULT_MAX_TOKENS", "1162"))

    # Generation parameter validation ranges
    temperature_min: float = 0.3
    temperature_max: float = 0.9
    top_p_min: float = 0.7
    top_p_max: float = 1.0
    repetition_penalty_min: float = 1.1
    repetition_penalty_max: float = 1.9

    # Internal voice names accepted directly by the model
    internal_voice_names: tuple[str, ...] = ("tara", "zac")
