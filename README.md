# Yap Text Inference Server

A single-process, GPU-accelerated text inference server optimized for low TTFT and steady streaming. It runs:
- vLLM chat engine (e.g., Gemma-2-9B)
- Hammer tool engine (e.g., Hammer-3B) for speculative decoding and tool-call detection
- LMCache local backend (CPU RAM + disk) for segment-level KV reuse (no Redis required)
- FastAPI + WebSocket streaming, Pipecat-friendly

## Key features
- Tool-call-first flow (Hammer). If toolcall is detected, we return immediately; else we stream chat tokens.
- Persona/history segmented prompts with LMCache KV reuse beyond prefixes.
- Speculative decoding (Hammer → Gemma) to increase tok/s and reduce latency.
- FP8/INT8 KV cache in vLLM to reduce VRAM and speed up decoding.
- Streaming text cleaner (emoji filtering, punctuation fixes, optional numeric conversions).
- Interrupts/barge-in via cancel or a new start.

## Quickstart (RunPod or any CUDA Linux image)

1) Install deps and start the server

```bash
bash scripts/main.sh
```

This will:
- Check GPU availability
- Install Python deps from `requirements.txt`
- Prepare LMCache local config (`/workspace/lmcache.yaml`) and store dir (`/workspace/lmcache_store`)
- Export environment defaults
- Launch `uvicorn src.server:app --port 8000`

2) Health check

```bash
curl -s http://127.0.0.1:8000/healthz
```

3) Stop (wipe runtime state but keep the repo and container services)

```bash
bash scripts/stop.sh
```

Stop script behavior:
- Terminates only `uvicorn src.server:app`
- Uninstalls pip deps from `requirements.txt`
- Removes common virtualenv dirs (`.venv`, `venv`, `env`, `.env`)
- Clears LMCache store, HF caches, pip/torch caches, NVIDIA PTX JIT cache
- Preserves the repository, the container, and services like Jupyter/web console

## Warmup test client

Use the local warmup client to open a WebSocket to the server, send a single start message, stream the full response, and print timing metrics.

First, activate the virtualenv created by the setup scripts:

```bash
source .venv/bin/activate
```

### Basic usage

```bash
python3 test/warmup.py
```

### With a custom message

```bash
python3 test/warmup.py "who was Columbus?"
```

### With gender/style flags

```bash
python3 test/warmup.py --gender male --style flirty "hello there"
```

### Environment overrides

- `SERVER_WS_URL` (default `ws://127.0.0.1:8000/ws`)
- `ASSISTANT_GENDER` (default `female`) — aliases accepted: `woman|man`
- `PERSONA_STYLE` (default `wholesome`)
- `RECV_TIMEOUT_SEC` (default `60`)

Examples:

```bash
SERVER_WS_URL=ws://127.0.0.1:8000/ws python3 test/warmup.py
RECV_TIMEOUT_SEC=120 python3 test/warmup.py --gender female --style nerdy "hey there"
```

### What it prints

- An ACK line confirming session seed/time and effective `assistant_gender`/`persona_style`.
- Two JSON lines when streaming completes:
  - Metrics: `{ "type": "metrics", "ttfb_ms": ..., "total_ms": ..., "stream_ms": ..., "chunks": ..., "chars": ... }`
  - Final text: `{ "type": "final_text", "text": "..." }`

The client matches the server protocol (ack → toolcall → token/final → done) and measures TTFB from the first streamed token.

## Environment variables (common)

Models and GPU split
- `CHAT_MODEL` (default `recoilme/recoilme-gemma-2-9B-v0.5`)
- `TOOL_MODEL` (default `MadeAgents/Hammer2.1-3b`)
- `CHAT_GPU_FRAC` (default `0.82`), `TOOL_GPU_FRAC` (default `0.14`)
- `KV_DTYPE` = `fp8` or `int8` (default `fp8`)

LMCache (local, no Redis)
- `USE_LMCACHE=1` (on)
- `LMCACHE_CONFIG_FILE=/workspace/lmcache.yaml` (provided)
- Optional Redis later: set `LMCACHE_REDIS_URI=redis://host:6379/0` (no code changes required)

Streaming/text processing
- `STREAM_RATE_TOKS_PER_S` (default `10`)
- `TEXTPROC_ENABLE=1` (enable cleaning)
- `TEXTPROC_REMOVE_EMOJIS=1`
- `TEXTPROC_CONVERT_NUMBERS=1` (time/math words)

Token limits
- `CHAT_MAX_OUT=200` (max assistant tokens per response)
- `HISTORY_MAX_TOKENS=3000` (rolling history cap; keeps most recent)
- `USER_UTT_MAX_TOKENS=500` (keeps beginning of user utterance)
- `EXACT_TOKEN_TRIM=1` (fast HF tokenizer for exact trimming; set `0` to disable)

All of the above have sensible defaults in `scripts/05_env_defaults.sh`.

## LMCache local config

`lmcache.yaml` (already in repo) enables local CPU RAM and disk store:
- Reuses KV for any repeated spans (not just prefixes)
- Persona/history are segmented so you can swap persona and keep history hot

To change sizes, edit `/workspace/lmcache.yaml` or the repo copy and rerun `scripts/main.sh`.

## API — WebSocket `/ws`

Messages you send
- Start a turn

```json
{
  "type": "start",
  "session_id": "<stable-per-user uuid>",
  "persona_text": "...optional full persona...",
  "persona_style": "nerdy|flirty|...",
  "assistant_gender": "woman|man",
  "user_identity": "woman|man|non-binary",
  "history_text": "...prior transcript...",
  "user_utterance": "hey—open spotify and queue my mix",
  "stream_rate_toks_per_s": 10
}
```

Notes
- If `persona_text` is omitted, it is composed from `persona_style`, `assistant_gender`, and `user_identity` using `prompts.py`.
- Incoming `user_utterance` is trimmed to the first 500 tokens.
- `history_text` is trimmed to keep the most recent ~3000 tokens.

- Cancel a turn

```json
{ "type": "cancel" }
```

- Warm persona/history (cache priming; optional)

```json
{ "type": "warm_persona", "persona_text": "..." }
{ "type": "warm_history", "history_text": "..." }
```

What you receive
- Tool-call decision (Hammer)

```json
{ "type": "toolcall", "status": "yes", "raw": "..." }
{ "type": "toolcall", "status": "no",  "raw": "..." }
```

- If `status":"no"`, steady token stream for chat

```json
{ "type": "token", "text": "..." }
...
{ "type": "done", "usage": {} }
```

Barge-in: send `cancel` or a new `start` with the same `session_id`.

## Persona and history behavior

- The chat prompt is structured as two explicit segments:
  - `<|persona|> ...` and `<|history|> ...`
- LMCache reuses any repeated spans. If you swap persona but keep the history bytes identical, the history KV stays hot.
- To guarantee a hit before speaking, send a `warm_persona` upfront.

## Streaming text cleaning

Enabled by default (`TEXTPROC_ENABLE=1`):
- Normalizes quotes, converts tabs to spaces, `%` → ` percent`, removes ` ;)` and "wink wink"
- Fixes two-space boundary to sentence period: `word  Word` → `word. Word`
- Removes emojis and collapses newlines/whitespace
- Adds final punctuation if missing (applied once at completion)
- Optional: time/math conversions to words (`TEXTPROC_CONVERT_NUMBERS=1`)

## Optimizations in this stack

- vLLM
  - Continuous batching + PagedAttention
  - `enforce_eager` + `enable_chunked_prefill` for low TTFT
  - FP8/INT8 KV cache (`KV_DTYPE`) for speed/VRAM
  - Speculative decoding
  - LMCache
  - Local CPU+disk backend, no Redis required
  - Segment-level reuse for persona/history; offload + reuse via connector
- Server
  - Toolcall-first routing (Hammer), then chat streaming
  - Steady 10 tok/s pacing for TTS friendliness
  - Interrupts via `abort_request`

## GPU reservations (GiB caps)

We reserve GPU memory per-engine via fractions, but this repo also supports GiB caps:

- Set `CHAT_GPU_GIB` and/or `TOOL_GPU_GIB` to fixed GiB. Code converts GiB → fraction safely.
- Fractions (`CHAT_GPU_FRAC`/`TOOL_GPU_FRAC`) act as fallback if GiB are unset.
- Defaults in `scripts/05_env_defaults.sh` are tuned for a 44.5 GiB card:
  - `CHAT_GPU_GIB=33.0`, `TOOL_GPU_GIB=7.0` (sum < total, leaves headroom)
  - `CHAT_MAX_LEN=4096` to reduce KV load; tool max len set to 1024 internally.

Example overrides:

```bash
export TOOL_GPU_GIB=7.0
export CHAT_GPU_GIB=33.0
unset TOOL_GPU_FRAC CHAT_GPU_FRAC
bash scripts/stop.sh && bash scripts/main.sh
```

## Limits and tradeoffs

- Chat outputs are capped at 200 tokens per response.
- Rolling history capped at ~3000 tokens (not counting persona). Long personas reduce remaining context.
- User utterances trimmed to first 500 tokens.
- Single-process, single-GPU by default. Under very high concurrency or very long contexts, you’ll be KV-bound. Scale by running another process or GPU; LMCache can be pointed at Redis for shared KV.

## Personality switching

- Send a new `start` with updated `persona_text` or new `persona_style`/`assistant_gender`/`user_identity`.
- Optionally warm the new persona via `warm_persona` to avoid first-turn spike.
