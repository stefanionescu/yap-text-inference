# Yap Text Inference Server

A single-process, GPU-accelerated text inference server optimized for low TTFT and steady streaming. It runs:
- vLLM chat engine (Impish Nemo 12B family)
- Hammer tool engine (e.g., Hammer-3B) for tool-call detection
- FastAPI + WebSocket streaming, Pipecat-friendly

## Key features
- Tool-call-first flow (Hammer). If toolcall is detected, we return immediately; else we stream chat tokens.
- Persona/history segmented prompts with prefix caching for KV reuse.
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
- Export environment defaults
- Launch `uvicorn src.server:app --port 8000`

### Viewing server logs

`05_start_server.sh` launches the server and writes logs to `server.log` at the repo root.

- Print the last 100 lines:

```bash
tail -n 100 server.log
```

- Follow logs live (Ctrl+C to stop following; server keeps running):

```bash
bash scripts/06_follow_logs.sh
# or
tail -F server.log
```

2) Health check

```bash
curl -s http://127.0.0.1:8000/healthz
```

3) Stop (deep clean by default; keeps the repo and container services)

```bash
bash scripts/stop.sh
```

Stop script behavior (defaults to deep clean):
- Terminates only `uvicorn src.server:app`
- Removes venv and purges pip caches
- Clears repo-local caches (`.hf`, `.vllm_cache`, `.torch_inductor`, `.triton`, `.flashinfer`, `.xformers`), tmp (`/tmp/vllm*`, `/tmp/flashinfer*`, `/tmp/torch_*`)
- Clears HF caches, torch caches, NVIDIA PTX JIT cache, and (by default) `$HOME/.cache`
- Preserves the repository, the container, and services like Jupyter/web console

Opt-out examples:

```bash
# Light clean (keep venv/home caches)
NUKE_ALL=0 bash scripts/stop.sh
```

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

## Benchmark client

Run concurrent sessions and report p50/p95 latencies:

```bash
python3 test/bench.py -n 32 -c 8
```

With a custom message and persona:

```bash
python3 test/bench.py --gender female --style flirty "who was Columbus?"
```

Override URL and timeout:

```bash
python3 test/bench.py --url ws://127.0.0.1:8000/ws -n 100 -c 20 --timeout 180
```

Environment alternatives:

- `SERVER_WS_URL` (default `ws://127.0.0.1:8000/ws`)
- `ASSISTANT_GENDER` (default `female`)
- `PERSONA_STYLE` (default `flirty`)

Outputs: totals and p50/p95 for `toolcall_ttfb_ms`, `chat_ttfb_ms`, and `first_sentence_ms`.

## Environment variables (common)

Models and GPU split
- `CHAT_MODEL` (default `SicariusSicariiStuff/Impish_Nemo_12B`)
- `TOOL_MODEL` (default `MadeAgents/Hammer2.1-3b`)
- `CHAT_GPU_FRAC` (default `0.75`), `TOOL_GPU_FRAC` (default `0.20`)
- `QUANTIZATION` = `none|fp8|gptq` (auto-detected; A100→`fp8` (W8A16), L40/L40S/H100→`fp8` (W8A8), 4‑bit mode→`gptq`)
- `KV_DTYPE` = `fp8_e5m2|auto` (auto; A100→`auto` (fp16), H100/L40S→`fp8_e5m2`)
- `VLLM_ATTENTION_BACKEND` (auto; prefers `FLASHINFER` if available, else `XFORMERS`)
- `dtype` is set to `auto` internally; no need to configure

LMCache: removed.

Streaming and concurrency
- `STREAM_FLUSH_MS` (default `0`; optional micro-coalescer in ms to reduce packet count)
- `CONCURRENT_MODEL_CALL` (default `0`; set to `1` to run chat and tool models concurrently instead of sequentially)

Token limits
- `CHAT_MAX_OUT=200` (max assistant tokens per response)
- `HISTORY_MAX_TOKENS=3000` (rolling history cap; keeps most recent)
- `USER_UTT_MAX_TOKENS=350` (keeps beginning of user utterance)
- `EXACT_TOKEN_TRIM=1` (fast HF tokenizer for exact trimming; set `0` to disable)

All of the above have sensible defaults in `scripts/04_env_defaults.sh`.

## KV caching
Using vLLM’s internal prefix caching with chunked prefill.

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
}
```

Notes
- If `persona_text` is omitted, it is composed from `persona_style`, `assistant_gender`, and `user_identity` using `prompts.py`.
- Incoming `user_utterance` is trimmed to the first 350 tokens.
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

## 4‑bit mode (GPTQ)

Run with 4‑bit weights using GPTQ quantization and the 4‑bit model:

```bash
bash scripts/main.sh 4-bit
```

Internally this selects `SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128`, sets `QUANTIZATION=gptq`, `dtype=auto`, and `KV_DTYPE=auto` (fp16) by default.

## Persona and history behavior

- The chat prompt is structured as two explicit segments:
  - `<|persona|> ...` and `<|history|> ...`
Prefix caching reuses any repeated spans within the process. If you swap persona but keep the history bytes identical, history KV stays hot.
- To guarantee a hit before speaking, send a `warm_persona` upfront.

## Optimizations in this stack

- vLLM
  - Continuous batching + PagedAttention
  - `enforce_eager` + `enable_chunked_prefill` for low TTFT
  - FP8/INT8 KV cache (`KV_DTYPE`) for speed/VRAM
  - Attention backend auto-select: FLASHINFER preferred (falls back to XFORMERS)
- Server
  - Toolcall-first routing (Hammer), then chat streaming
  - Realtime token streaming by default (no artificial pacing)
  - Interrupts via `abort_request`

## GPU memory fractions

We reserve GPU memory per-engine via fractions only:

- Defaults: `CHAT_GPU_FRAC=0.75`, `TOOL_GPU_FRAC=0.20`.
- Override as needed:

```bash
export CHAT_GPU_FRAC=0.80
export TOOL_GPU_FRAC=0.15
bash scripts/stop.sh && bash scripts/main.sh
```

Note: `CHAT_MAX_LEN` defaults to `5760`; adjust to trade off KV usage vs context.

## Limits and tradeoffsf

- Chat outputs are capped at 200 tokens per response.
- Rolling history capped at ~3000 tokens (not counting persona). Long personas reduce remaining context.
- User utterances trimmed to first 350 tokens.
- Single-process, single-GPU by default. Under very high concurrency or very long contexts, you’ll be KV-bound. Scale by running another process or GPU.

## Personality switching

- Send a new `start` with updated `persona_text` or new `persona_style`/`assistant_gender`/`user_identity`.
- Optionally warm the new persona via `warm_persona` to avoid first-turn spike.
