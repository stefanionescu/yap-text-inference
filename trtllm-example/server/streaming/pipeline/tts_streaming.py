"""TRT-LLM audio streaming."""

from collections.abc import Awaitable, Callable, Iterable

from tensorrt_llm import SamplingParams

from server.audio.audio_decoder import AudioDecoder, TokenProcessor
from server.audio.silence import SilenceTrimConfig, SilenceTrimmer
from server.config import settings
from server.text.prompts import build_prompt
from server.voices import resolve_voice


async def aiter_pcm_from_custom_tokens(
    engine,
    prompt: str,
    voice: str,
    sp: SamplingParams,
    trim_silence: bool = True,
    prepad_ms: float | None = None,
    token_observer: Callable[[Iterable[int]], Awaitable[None]] | None = None,
):  # noqa: PLR0912
    """
    TRT-LLM streaming: read token_ids deltas, not detokenized text.
    Map Orpheus audio token ids → 7-stream RVQ codes → SNAC decode.
    """
    # Build the Orpheus prompt
    # Accept internal names directly; resolve only external aliases
    resolved_voice = voice if voice in settings.internal_voice_names else resolve_voice(voice)
    formatted = build_prompt(prompt, resolved_voice)

    # Initialize clean decoder, processor, and silence trimmer
    decoder = AudioDecoder()
    processor = TokenProcessor(decoder)
    trimmer = SilenceTrimmer(
        SilenceTrimConfig(
            sample_rate=decoder.sample_rate,
            enabled=bool(trim_silence),
            rms_threshold=settings.silence_rms_threshold,
            activation_ms=settings.silence_activation_ms,
            prepad_ms=(prepad_ms if prepad_ms is not None else settings.silence_prespeech_pad_ms),
            max_leading_sec=settings.silence_max_leading_sec,
            sustain_ms=settings.silence_sustain_ms,
            noise_window_sec=settings.silence_noise_window_sec,
            noise_percentile=settings.silence_noise_percentile,
            threshold_multiplier=settings.silence_threshold_multiplier,
        )
    )
    prev_len = 0

    # Stream tokens and process audio codes
    async for chunk in engine.generate_async(formatted, sp, streaming=True):
        if not getattr(chunk, "outputs", None):
            continue

        out = chunk.outputs[0]
        tids = getattr(out, "token_ids", None)
        if not tids:
            # Some TRT builds deliver `output_token_ids` instead
            tids = getattr(out, "output_token_ids", None)
        if not tids:
            continue

        new_tokens = tids[prev_len:]
        if not new_tokens:
            continue
        prev_len = len(tids)

        if token_observer is not None:
            await token_observer(new_tokens)

        # Process each new token
        for token_id in new_tokens:
            frames_ready = processor.process_token(token_id)
            if frames_ready is not None:
                chunk_bytes = await processor.emit_window(frames_ready)
                if chunk_bytes:
                    if trim_silence:
                        trimmed = trimmer.push(chunk_bytes)
                        if trimmed:
                            yield trimmed
                    else:
                        yield chunk_bytes

    # Emit final window for remaining frames
    final_bytes = await processor.emit_final_window()
    if final_bytes:
        if trim_silence:
            trimmed = trimmer.push(final_bytes)
            if trimmed:
                yield trimmed
        else:
            yield final_bytes
    # Flush any pending buffered audio in the trimmer (e.g., if activation never exceeded threshold)
    if trim_silence:
        flushed = trimmer.flush()
        if flushed:
            yield flushed
