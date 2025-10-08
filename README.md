# Yap Text Inference Server

A single-process, GPU-accelerated text inference server optimized for low TTFT and steady streaming. It can run:
- vLLM chat engine with chat models ranging from 3B-24B
- Hammer tool engine (e.g., Hammer 2.1 3B or 1.5B) for tool-call detection
- Both engines together, or deploy chat-only or tool-only for specialized use cases
- FastAPI + WebSocket streaming, Pipecat-friendly

## Key features
- Tool-call-first detection (Hammer). Toolcall signal is sent when detected, then (when chat is deployed) chat tokens always stream regardless.
- Persona/history segmented prompts with prefix caching for KV reuse.
- FP8/INT8 KV cache in vLLM to reduce VRAM and speed up decoding.
- Interrupts/barge-in via cancel or a new start.
- Concurrent connection limiting to protect GPU resources (deployment-aware: 32 for tool-only, 24 for chat-only, 16 for both)
- API key authentication for secure access (configurable, default: "yap_token")

## Quickstart (RunPod or any CUDA Linux image)

1) Install deps and start the server

```bash
# Both models (default)
bash scripts/main.sh [awq] <chat_model> <tool_model> [deploy_mode]

# Single-model forms
bash scripts/main.sh [awq] chat <chat_model>
bash scripts/main.sh [awq] tool <tool_model>
```

Examples:
```bash
# Float chat model (auto → FP8)
bash scripts/main.sh SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b

# Float roleplay model (auto → FP8)
bash scripts/main.sh SicariusSicariiStuff/Wingless_Imp_8B MadeAgents/Hammer2.1-1.5b

# Concurrent mode for faster response (auto → FP8)
CONCURRENT_MODEL_CALL=1 bash scripts/main.sh SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b

# GPTQ chat model (auto → GPTQ) with concurrent mode
CONCURRENT_MODEL_CALL=1 bash scripts/main.sh SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64 MadeAgents/Hammer2.1-3b

# 4-bit AWQ auto-quantization with concurrent mode (quantizes both chat and tool on load)
CONCURRENT_MODEL_CALL=1 bash scripts/main.sh awq SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b

# Chat-only deployment (auto determines FP8/GPTQ)
bash scripts/main.sh chat SicariusSicariiStuff/Impish_Nemo_12B

# Tool-only deployment
bash scripts/main.sh tool MadeAgents/Hammer2.1-1.5b
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

2) Health check (no authentication required)

```bash
curl -s http://127.0.0.1:8000/healthz
```

3) Monitor server status and capacity (requires API key)

```bash
# With default API key
curl -H "X-API-Key: yap_token" http://127.0.0.1:8000/status

# With custom API key
curl -H "X-API-Key: your_custom_key" http://127.0.0.1:8000/status

# Via query parameter
curl "http://127.0.0.1:8000/status?api_key=yap_token"
```

Returns server status and connection capacity information, including current active connections and limits.

4) Stop (deep clean by default; keeps the repo and container services)

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

## Security Configuration

**API Key Setup:**
```bash
# Use default API key (yap_token)
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000

# Set custom API key before starting server
export YAP_API_KEY="my_super_secret_key_2024"
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000
```

**Connection Limiting:**
```bash
# Set custom connection limit (default: 24)
export MAX_CONCURRENT_CONNECTIONS=50
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000
```

**Authentication Coverage:**
- ✅ **`/healthz`** - No authentication required (for load balancers/monitoring)
- 🔐 **`/status`** - Requires API key  
- 🔐 **`/ws`** - Requires API key

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

### Testing concurrent vs sequential modes

Compare performance between sequential and concurrent model calling:

```bash
# Test sequential mode (default)
python3 test/warmup.py "write a simple hello world function"

# Test concurrent mode (restart server first)
# Terminal 1: Start server with concurrent mode (auto → FP8)
CONCURRENT_MODEL_CALL=1 bash scripts/main.sh SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b

# Terminal 2: Test the same query
python3 test/warmup.py "write a simple hello world function"

# Test the roleplay-optimized model
# Terminal 1: Start server with Wingless_Imp_8B (auto → FP8)
bash scripts/main.sh SicariusSicariiStuff/Wingless_Imp_8B MadeAgents/Hammer2.1-1.5b

# Terminal 2: Test creative/roleplay query
python3 test/warmup.py "*waves hand* Tell me a creative story about a lonely dragon"
```

The concurrent mode should show lower `ttfb_ms` (time to first byte) for chat responses that don't involve tool calls.

### Environment overrides

- `SERVER_WS_URL` (default `ws://127.0.0.1:8000/ws`)
- `ASSISTANT_GENDER` (default `female`) — aliases accepted: `woman|man`
- `PERSONA_STYLE` (default `wholesome`)
- `RECV_TIMEOUT_SEC` (default `60`)

Examples:

```bash
SERVER_WS_URL=ws://127.0.0.1:8000/ws python3 test/warmup.py
RECV_TIMEOUT_SEC=120 python3 test/warmup.py --gender female --style savage "hey there"
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

### Benchmarking concurrent vs sequential modes

Compare performance characteristics between modes:

```bash
# Benchmark sequential mode (default server)
python3 test/bench.py -n 50 -c 8 "explain how machine learning works"

# Stop server and restart with concurrent mode (auto → FP8)
bash scripts/stop.sh
CONCURRENT_MODEL_CALL=1 bash scripts/main.sh SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b

# Benchmark concurrent mode
python3 test/bench.py -n 50 -c 8 "explain how machine learning works"
```

For chat-heavy workloads, concurrent mode typically shows:
- ✅ Lower `chat_ttfb_ms` (faster first token)
- ⚠️ Slightly higher resource usage
- ⚠️ May show higher `toolcall_ttfb_ms` when tools are actually needed

## Pipecat Integration

The server is designed for seamless [Pipecat](https://github.com/pipecat-ai/pipecat) integration with persistent connections and real-time interruption:

**Key features for Pipecat:**
- ✅ **Long-term WebSocket connections** - One connection per user, stays open indefinitely
- ✅ **Session-based user assignment** - Each user gets a unique `session_id` 
- ✅ **Automatic barge-in** - New messages cancel ongoing generation (perfect for voice interruption)
- ✅ **Persistent session state** - Persona, settings maintained across requests
- ✅ **Real-time streaming** - Tokens stream immediately with minimal buffering
- ✅ **Concurrent model support** - Optional concurrent mode for lowest latency

Environment alternatives:

- `SERVER_WS_URL` (default `ws://127.0.0.1:8000/ws`)
- `ASSISTANT_GENDER` (default `female`)
- `PERSONA_STYLE` (default `flirty`)
- `YAP_API_KEY` (default `yap_token`) - API key for authentication

**Note**: All test clients now require API key authentication. Ensure `YAP_API_KEY` matches your server configuration.

Outputs: totals and p50/p95 for `toolcall_ttfb_ms`, `chat_ttfb_ms`, and `first_sentence_ms`.

## Environment variables (common)

Server configuration
- `YAP_API_KEY` (default `yap_token`) - API key for authentication (all endpoints except `/healthz`)
- `MAX_CONCURRENT_CONNECTIONS` - Maximum concurrent WebSocket connections (deployment-aware: 32 for tool-only, 24 for chat-only, 16 for both)
- `DEPLOY_MODELS` (default `both`) - Which models to deploy: `both`, `chat`, or `tool`

Models and GPU split
- `CHAT_MODEL` (required when deploying chat)
- `TOOL_MODEL` (required when deploying tool: `MadeAgents/Hammer2.1-1.5b` or `MadeAgents/Hammer2.1-3b`)
- `CHAT_GPU_FRAC`, `TOOL_GPU_FRAC` - GPU memory allocation (deployment-aware: 90% for single-model, 70%/20% for both)
- `QUANTIZATION` (auto-set by `scripts/main.sh`): GPTQ if chat repo contains `GPTQ`, else FP8; explicit `awq` supported
- `KV_DTYPE` = `fp8|auto|int8` (auto-selected based on GPU and quantization mode)
- `VLLM_ATTENTION_BACKEND` (auto; prefers `FLASHINFER` if available, else `XFORMERS`)
- `dtype` is set to `auto` internally; no need to configure

Streaming and concurrency
- `STREAM_FLUSH_MS` (default `0`; optional micro-coalescer in ms to reduce packet count)
- `CONCURRENT_MODEL_CALL` (default `0`; set to `1` to run chat and tool models concurrently instead of sequentially)
  - Sequential mode: Tool model runs first, then chat model always runs (safer, lower resource usage)
  - Concurrent mode: Both models start together, chat buffered until tool decision, then chat always continues (faster response, higher resource usage)

Token limits
- `CHAT_MAX_OUT=200` (max assistant tokens per response)
- `HISTORY_MAX_TOKENS=3000` (rolling history cap; keeps most recent)
- `USER_UTT_MAX_TOKENS=350` (keeps beginning of user utterance)
- `EXACT_TOKEN_TRIM=1` (fast HF tokenizer for exact trimming; set `0` to disable)

All of the above have sensible defaults in `scripts/04_env_defaults.sh`.

## KV caching
Using vLLM’s internal prefix caching with chunked prefill.

### Log rotation
Example logrotate config (optional):

```
/path/to/repo/server.log {
  size 100M
  rotate 3
  copytruncate
  compress
  missingok
}
```

Or rely on the built-in simple rotation in `scripts/06_follow_logs.sh` which rotates at ~100MB once to `server.log.1`.

## API — WebSocket `/ws`

The server maintains persistent WebSocket connections with session-based user assignment. Each client provides a `session_id` for user identification, and the connection can handle multiple requests over time with automatic interruption support.

**🔐 Authentication Required**: All WebSocket connections require API key authentication via query parameter or header.

**Connection lifecycle:**
1. Client connects to `ws://server:8000/ws?api_key=your_key` (with authentication)
2. Client sends `start` message with `session_id` to assign/identify user  
3. Connection stays open for multiple requests (up to server connection limit)
4. Session state (persona, settings) persists across requests
5. New `start` messages automatically cancel previous requests (barge-in)
6. Connections are limited to protect GPU resources (default: 24 concurrent)

**Authentication methods:**
```javascript
// Via query parameter (recommended for WebSocket)
const ws = new WebSocket('ws://server:8000/ws?api_key=yap_token');

// Via header (if supported by client)
const ws = new WebSocket('ws://server:8000/ws', [], {
  headers: { 'X-API-Key': 'yap_token' }
});
```

**Connection limit handling:**
- If server is at capacity, connection will be rejected with error code `server_at_capacity`
- Clients should implement retry logic with exponential backoff

Messages you send
- Start a turn

```json
{
  "type": "start",
  "session_id": "<stable-per-user uuid>",
  "persona_text": "...optional full persona...",
  "persona_style": "savage|flirty|...",
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
- **Authentication errors** (if API key is missing or invalid)

```json
{
  "type": "error",
  "error_code": "authentication_failed",
  "message": "Authentication required. Provide valid API key via 'api_key' query parameter or 'X-API-Key' header."
}
```

- **Capacity errors** (if server is at maximum connections)

```json
{
  "type": "error",
  "error_code": "server_at_capacity",
  "message": "Server is at capacity. Active connections: 24/24. Please try again later.",
  "capacity": {"active": 24, "max": 24, "available": 0, "at_capacity": true}
}
```

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

### Barge-in and cancellation

The server supports real-time interruption for natural conversation flow:

**Explicit cancellation:**
```json
{"type": "cancel"}
```

**Automatic barge-in (recommended for Pipecat):**
```json
{"type": "start", "session_id": "user123", "user_utterance": "new message"}
```
- New `start` messages automatically cancel any ongoing generation for that session
- Perfect for real-time conversation interruption when users start speaking
- Both chat and tool models are immediately aborted
- New response begins streaming right away

**Response handling:**
- Cancelled requests return: `{"type": "done", "cancelled": true}`
- New requests stream normally with `token` messages

## Quantization modes

By default, quantization is implicit:
- If the chat model repo name contains "GPTQ" → GPTQ (gptq_marlin).
- Otherwise → FP8 (8-bit).

You can explicitly select AWQ:

**4-bit mode (AWQ via vLLM auto-AWQ):**
```bash
# Uses float (non-GPTQ) chat model weights and quantizes BOTH chat and tool models at load
bash scripts/main.sh awq SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b

# With concurrent mode
CONCURRENT_MODEL_CALL=1 bash scripts/main.sh awq SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b
```

Notes for AWQ:
- Provide a float chat model (e.g., `SicariusSicariiStuff/Impish_Nemo_12B`, `kyx0r/Neona-12B`, `SicariusSicariiStuff/Wingless_Imp_8B`, etc.) — do not pass a GPTQ repo.
- The tool model (`MadeAgents/Hammer2.1-1.5b` or `-3b`) is also quantized to 4-bit AWQ on load for consistency.
- AWQ requires additional wheels (installed automatically via `requirements.txt`).

## Model calling modes

The server supports two model calling modes:

**Sequential mode (default):**
- Tool model runs first to detect function calls
- Chat model always runs after tool decision (regardless of tool detection)
- Lower resource usage, predictable behavior  
- Good for most use cases

```bash
# Sequential mode (default for roleplay)
bash scripts/main.sh 8bit SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b

# Sequential mode (roleplay/creative optimized)
bash scripts/main.sh 8bit SicariusSicariiStuff/Wingless_Imp_8B MadeAgents/Hammer2.1-3b

# Sequential mode (highest rated uncensored)
bash scripts/main.sh 8bit SicariusSicariiStuff/Impish_Mind_8B MadeAgents/Hammer2.1-3b

# Sequential mode (flagship 24B model)
bash scripts/main.sh 8bit SicariusSicariiStuff/Impish_Magic_24B MadeAgents/Hammer2.1-3b

# Sequential mode (exceptional 5B roleplay)
bash scripts/main.sh 8bit SicariusSicariiStuff/Eximius_Persona_5B MadeAgents/Hammer2.1-3b

# Sequential mode (compact 4B roleplay)
bash scripts/main.sh 8bit SicariusSicariiStuff/Impish_LLAMA_4B MadeAgents/Hammer2.1-3b

# Sequential mode (creative 3B roleplay)
bash scripts/main.sh 8bit SicariusSicariiStuff/Fiendish_LLAMA_3B MadeAgents/Hammer2.1-3b
```

**Concurrent mode:**
- Both chat and tool models start simultaneously
- Chat tokens are buffered while waiting for tool decision
- If tool call detected: chat stream is cancelled, tool response sent, then new chat stream starts
- If no tool call: buffered chat text is flushed immediately, streaming continues
- Faster perceived response time for chat interactions
- Higher resource usage (both models running)

```bash
# Enable concurrent mode
CONCURRENT_MODEL_CALL=1 bash scripts/main.sh 8bit SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b
```

**When to use concurrent mode:**
- ✅ High-performance scenarios where latency matters most
- ✅ Workloads with mostly chat interactions (few tool calls)  
- ✅ Systems with sufficient GPU memory and compute
- ❌ Resource-constrained environments
- ❌ Workloads with frequent tool calls (wasted compute)

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
  - **Modular architecture** - Clean separation of concerns (handlers/, execution/, utils/)
  - **Connection limiting** - Protects GPU resources from overload
  - **API key authentication** - Secure access with configurable keys
  - Toolcall detection (Hammer), then chat streaming always continues
  - Realtime token streaming by default (no artificial pacing)
  - Interrupts via `abort_request`
  - Thread-safe session and connection management

## GPU memory fractions

GPU memory is allocated based on deployment mode:

- **Single model**: 90% GPU memory (chat-only or tool-only)
- **Both models**: Chat gets 70%, Tool gets 20%
- Override as needed:

```bash
export CHAT_GPU_FRAC=0.80
export TOOL_GPU_FRAC=0.15
bash scripts/stop.sh && bash scripts/main.sh
```

Note: `CHAT_MAX_LEN` defaults to `5760`; adjust to trade off KV usage vs context.

## Limits and tradeoffs

- Chat outputs are capped at 200 tokens per response.
- Rolling history capped at ~3000 tokens (not counting persona). Long personas reduce remaining context.
- User utterances trimmed to first 350 tokens.
- **Concurrent connections limited** (deployment-aware: 32 for tool-only, 24 for chat-only, 16 for both) to protect GPU resources from overload.
- Single-process, single-GPU by default. Under very high concurrency or very long contexts, you'll be KV-bound. Scale by running another process or GPU.
- **Authentication required** for all API access except health checks.

## Personality switching

- Send a new `start` with updated `persona_text` or new `persona_style`/`assistant_gender`/`user_identity`.
- Optionally warm the new persona via `warm_persona` to avoid first-turn spike.
