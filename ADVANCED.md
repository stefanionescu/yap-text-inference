# Yap Text Inference Advanced Guide

This document covers advanced operations, configuration, and deep-dive details.

## Viewing Logs

All deployment and server logs are unified in a single `server.log` file.

```bash
# All logs (deployment + server activity)
tail -f server.log
```

Note: `scripts/main.sh` auto-tails all logs by default. Ctrl+C detaches from tail without stopping the deployment.

## Quick Operations

After initial deployment, you can use these commands to stop and/or restart the server:

```bash
# Light stop (preserve AWQ models and dependencies)
NUKE_ALL=0 bash scripts/stop.sh

# Quick restart using existing AWQ models
bash scripts/restart.sh [both|chat|tool]

# Full stop and restart cycle
bash scripts/stop.sh && bash scripts/main.sh awq <chat_model> <tool_model>
```

## Health Check

```bash
curl -s http://127.0.0.1:8000/healthz
```

## Server Status and Capacity

```bash
# With default API key
curl -H "X-API-Key: yap_token" http://127.0.0.1:8000/status

# With custom API key
curl -H "X-API-Key: your_custom_key" http://127.0.0.1:8000/status

# Via query parameter
curl "http://127.0.0.1:8000/status?api_key=yap_token"
```

Returns server status and connection capacity information, including current active connections and limits.

## Stop Script Behavior (Deep Clean)

Default behavior (deep clean):
- Terminates only `uvicorn src.server:app`
- Removes venv and purges pip caches
- Clears repo-local caches (`.hf`, `.vllm_cache`, `.torch_inductor`, `.triton`, `.flashinfer`, `.xformers`), tmp (`/tmp/vllm*`, `/tmp/flashinfer*`, `/tmp/torch_*`)
- Clears HF caches, torch caches, NVIDIA PTX JIT cache, and (by default) `$HOME/.cache`
- Preserves the repository, the container, and services like Jupyter/web console

Opt-out example:

```bash
# Light clean (keep venv/home caches)
NUKE_ALL=0 bash scripts/stop.sh
```

## Quick Restart (Local and Hugging Face AWQ Models)

The restart script works with both local and Hugging Face AWQ models.

```bash
# Quick restart (auto-detects local or HF models)
bash scripts/restart.sh [both|chat|tool]

# Examples with different sources:
bash scripts/restart.sh                                    # Local models (if available)
AWQ_CHAT_MODEL=yapwithai/impish-12b-awq bash scripts/restart.sh chat
AWQ_TOOL_MODEL=yapwithai/hammer-2.1-3b-awq bash scripts/restart.sh tool
AWQ_CHAT_MODEL=yapwithai/impish-12b-awq AWQ_TOOL_MODEL=yapwithai/hammer-2.1-3b-awq bash scripts/restart.sh both

# Sequential mode restart
CONCURRENT_MODEL_CALL=0 bash scripts/restart.sh
```

How it works:
- Smart detection of local `.awq/` cache vs. `AWQ_CHAT_MODEL`/`AWQ_TOOL_MODEL`
- Stops server with light clean (preserves models and dependencies)
- Starts server directly using detected AWQ models
- Skips GPU check, dependency install, and quantization
- For HF models: Auto-creates venv/deps if missing

## Security Configuration

### API Key Setup

```bash
# Use default API key (yap_token)
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000

# Set custom API key before starting server
export YAP_TEXT_API_KEY="my_super_secret_key_2024"
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000
```

### Connection Limiting (Deployment/Quantization-Aware)

```bash
# Set custom connection limit (defaults vary by mode)
export MAX_CONCURRENT_CONNECTIONS=50
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000
```

### Authentication Coverage

- `/healthz` – No authentication required
- `/status` – Requires API key
- `/ws` – Requires API key

## Environment Variables

Server configuration
- `YAP_TEXT_API_KEY` (default `yap_token`) – API key for authentication (all endpoints except `/healthz`)
- `MAX_CONCURRENT_CONNECTIONS` – Maximum concurrent WebSocket connections (deployment/quantization-aware; defaults vary)
- `DEPLOY_MODELS` (default `both`) – Which models to deploy: `both`, `chat`, or `tool`

Models and GPU split
- `CHAT_MODEL` (required when deploying chat)
- `TOOL_MODEL` (required when deploying tool: `MadeAgents/Hammer2.1-1.5b` or `MadeAgents/Hammer2.1-3b`)
- `AWQ_CHAT_MODEL` – Use pre-quantized AWQ chat model from HF instead of local quantization
- `AWQ_TOOL_MODEL` – Use pre-quantized AWQ tool model from HF instead of local quantization
- `CHAT_GPU_FRAC`, `TOOL_GPU_FRAC` – GPU memory allocation
- `QUANTIZATION` – Auto-set by `scripts/main.sh`: GPTQ if chat repo contains `GPTQ`, else FP8; explicit `awq` supported
- `KV_DTYPE` = `fp8|auto|int8` – Auto-selected based on GPU and quantization mode
- `VLLM_ATTENTION_BACKEND` – Auto; prefers `FLASHINFER` if available, else `XFORMERS`
- `dtype` is set to `auto` internally; no need to configure

Streaming and concurrency
- `STREAM_FLUSH_MS` (default `0`) – Optional micro-coalescer in ms to reduce packet count
- `CONCURRENT_MODEL_CALL` (default `0`) – Set to `1` to run chat and tool models concurrently instead of sequentially
  - Sequential mode: Tool model runs first, then chat model always runs
  - Concurrent mode: Both models start together, chat buffered until tool decision

Token limits
- `CHAT_MAX_OUT=200` – Max assistant tokens per response
- `HISTORY_MAX_TOKENS=3000` – Rolling history cap (keeps most recent)
- `USER_UTT_MAX_TOKENS=350` – Keeps beginning of user utterance
- `EXACT_TOKEN_TRIM=1` – Fast HF tokenizer for exact trimming; set `0` to disable

Networking and downloads
- `HF_HUB_ENABLE_HF_TRANSFER` (default `0` in scripts): Opt-in to Hugging Face transfer acceleration.

All of the above have sensible defaults in `scripts/04_env_defaults.sh`.

## Log Rotation

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

The deployment system has built-in rotation for `server.log` which rotates at ~100MB automatically.

## API — WebSocket `/ws`

The server maintains persistent WebSocket connections with session-based user assignment. Each client provides a `session_id` for user identification, and the connection can handle multiple requests over time with automatic interruption support.

### Connection Lifecycle
1. Client connects to `ws://server:8000/ws?api_key=your_key` (with authentication)
2. Client sends `start` message with `session_id` to assign/identify user
3. Connection stays open for multiple requests (up to server connection limit)
4. Session state (persona, settings) persists across requests
5. New `start` messages automatically cancel previous requests (barge-in)
6. Connections are limited to protect GPU resources

### Authentication Methods
```javascript
// Via query parameter (recommended for WebSocket)
const ws = new WebSocket('ws://server:8000/ws?api_key=yap_token');

// Via header (if supported by client)
const ws = new WebSocket('ws://server:8000/ws', [], {
  headers: { 'X-API-Key': 'yap_token' }
});
```

### Connection Limit Handling
- If server is at capacity, connection will be rejected with error code `server_at_capacity`
- Clients should implement retry logic with exponential backoff

### Messages You Send

Start a turn

```json
{
  "type": "start",
  "session_id": "<stable-per-user uuid>",
  "persona_text": "...optional full persona...",
  "persona_style": "savage|flirty|...",
  "assistant_gender": "woman|man",
  "user_identity": "woman|man|non-binary",
  "history_text": "...prior transcript...",
  "user_utterance": "hey—open spotify and queue my mix"
}
```

Cancel a turn

```json
{ "type": "cancel" }
```

Warm persona/history (cache priming; optional)

```json
{ "type": "warm_persona", "persona_text": "..." }
{ "type": "warm_history", "history_text": "..." }
```

### What You Receive

Authentication errors

```json
{
  "type": "error",
  "error_code": "authentication_failed",
  "message": "Authentication required. Provide valid API key via 'api_key' query parameter or 'X-API-Key' header."
}
```

Capacity errors

```json
{
  "type": "error",
  "error_code": "server_at_capacity",
  "message": "Server is at capacity.",
  "capacity": {"active": 24, "max": 24, "available": 0, "at_capacity": true}
}
```

Tool-call decision

```json
{ "type": "toolcall", "status": "yes", "raw": "..." }
{ "type": "toolcall", "status": "no",  "raw": "..." }
```

In both-model deployments, chat tokens always stream after the toolcall decision (for both `"yes"` and `"no"`).

### Barge-In and Cancellation

Explicit cancellation:

```json
{"type": "cancel"}
```

Automatic barge-in (recommended for Pipecat):

```json
{"type": "start", "session_id": "user123", "user_utterance": "new message"}
```

- New `start` messages automatically cancel any ongoing generation for that session
- Both chat and tool models are immediately aborted; new response begins streaming right away

Response handling:
- Cancelled requests return: `{ "type": "done", "cancelled": true }`
- New requests stream normally with `token` messages

## Quantization Notes

Notes for AWQ:
- Local quantization: Provide a float chat model (e.g., `SicariusSicariiStuff/Impish_Nemo_12B`, `kyx0r/Neona-12B`, `SicariusSicariiStuff/Wingless_Imp_8B`, etc.) — do not pass a GPTQ repo
- Pre-quantized models: Use `AWQ_CHAT_MODEL` and/or `AWQ_TOOL_MODEL` environment variables to specify HF repos with pre-quantized AWQ models
- Smart detection: Any Hugging Face repo containing "awq" in the name will be automatically accepted when using AWQ quantization
- The tool model (`MadeAgents/Hammer2.1-1.5b` or `-3b`) is also quantized to 4-bit AWQ on load for consistency (local mode)
- AWQ requires additional wheels (installed automatically via `requirements.txt`)
- Auth for private/gated repos: Set `HUGGINGFACE_HUB_TOKEN` or `HF_TOKEN`
- Cache location: This repo standardizes on `HF_HOME` (override with `export HF_HOME=/path/to/cache`)
- Networking: For script-based deployments, HF transfer acceleration is disabled by default; opt in with `HF_HUB_ENABLE_HF_TRANSFER=1` when supported

### Pushing AWQ Exports to Hugging Face

When `QUANTIZATION=awq`, the deployment pipeline can upload the freshly quantized folders to the Hugging Face Hub. Uploads are opt-in and controlled via environment variables:

```bash
export HF_AWQ_PUSH=1                           # enable uploads (quits early if token/repos missing)
export HF_TOKEN="hf_your_api_token"            # token with write access
export HF_AWQ_CHAT_REPO="your-org/chat-awq"    # repo for the chat model (required if chat deployed)
export HF_AWQ_TOOL_REPO="your-org/tool-awq"    # repo for the tool model (required if tool deployed)
# optional tweaks
export HF_AWQ_BRANCH=main                      # branch name (default: main)
export HF_AWQ_PRIVATE=1                        # create repo as private (0 = public)
export HF_AWQ_ALLOW_CREATE=1                   # create repo automatically (0 = expect it to exist)
export HF_AWQ_COMMIT_MSG_CHAT="Upload Nemo AWQ build"   # optional commit message override
export HF_AWQ_COMMIT_MSG_TOOL="Upload Hammer AWQ build"

# now run the usual launcher
HF_AWQ_PUSH=1 scripts/main.sh awq <chat_model> <tool_model>
```

The pipeline writes `awq_metadata.json` and `README.md` into each quantized folder for transparency and reproducibility.

## Persona and History Behavior

- The chat prompt is structured as two explicit segments: `<|persona|> ...` and `<|history|> ...`
- Prefix caching reuses any repeated spans within the process. If you swap persona but keep the history bytes identical, history KV stays hot.
- To guarantee a hit before speaking, send a `warm_persona` upfront.

## Optimizations in This Stack

- vLLM
  - Continuous batching + PagedAttention
  - `enforce_eager` + `enable_chunked_prefill` for low TTFT
  - FP8/INT8 KV cache (`KV_DTYPE`) for speed/VRAM
  - Attention backend auto-select: FLASHINFER preferred (falls back to XFORMERS)
- Server
  - Modular architecture – Clean separation of concerns (`handlers/`, `execution/`, `utils/`)
  - Connection limiting – Protects GPU resources from overload
  - API key authentication – Secure access with configurable keys
  - Toolcall detection, then chat streaming always continues
  - Realtime token streaming by default (no artificial pacing)
  - Interrupts via `abort_request`
  - Thread-safe session and connection management

## GPU Memory Fractions

GPU memory is allocated based on deployment mode:

- Single model: 90% GPU memory (chat-only or tool-only)
- Both models: Chat gets 70%, Tool gets 20%

Override as needed:

```bash
export CHAT_GPU_FRAC=0.80
export TOOL_GPU_FRAC=0.15
bash scripts/stop.sh && bash scripts/main.sh
```


