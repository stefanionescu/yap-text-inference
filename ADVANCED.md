# Yap Text Inference Advanced Guide

This document covers advanced operations, configuration, and deep-dive details.

## Contents

- [Security Configuration](#security-configuration)
  - [API Key Setup](#api-key-setup)
  - [Connection Limiting (Deployment/Quantization-Aware)](#connection-limiting-deploymentquantization-aware)
  - [Authentication Coverage](#authentication-coverage)
- [Log Rotation](#log-rotation)
- [API — WebSocket `/ws`](#api--websocket-ws)
  - [Connection Lifecycle](#connection-lifecycle)
  - [Authentication Methods](#authentication-methods)
  - [Connection Limit Handling](#connection-limit-handling)
  - [Messages You Send](#messages-you-send)
  - [What You Receive](#what-you-receive)
  - [Barge-In and Cancellation](#barge-in-and-cancellation)
- [Quantization Notes](#quantization-notes)
  - [Pushing AWQ Exports to Hugging Face](#pushing-awq-exports-to-hugging-face)
- [Persona and History Behavior](#persona-and-history-behavior)
- [GPU Memory Fractions](#gpu-memory-fractions)

## Security Configuration

### Required Environment Variables

Set these before running `scripts/main.sh`, `scripts/restart.sh`, or any host utility:

```bash
export TEXT_API_KEY="my_super_secret_key_2024"  # Required for every request
export HF_TOKEN="hf_your_api_token"             # Required to access HF models
export MAX_CONCURRENT_CONNECTIONS=50            # Required capacity guard (choose per hardware)
```

`HUGGINGFACE_HUB_TOKEN` can be set instead of `HF_TOKEN`; the host scripts automatically mirror it.

### API Key Setup

```bash
# TEXT_API_KEY is required and must be set before starting the server
export TEXT_API_KEY="my_super_secret_key_2024"
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000
```

### Connection Limiting (Manual Capacity Selection)

```bash
# Set the connection limit explicitly (no automatic defaults)
export MAX_CONCURRENT_CONNECTIONS=50
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000
```

### Authentication Coverage

- `/healthz` – No authentication required
- `/status` – Requires API key
- `/ws` – Requires API key

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
const ws = new WebSocket('ws://server:8000/ws?api_key=your_api_key');

// Via header (if supported by client)
const ws = new WebSocket('ws://server:8000/ws', [], {
  headers: { 'X-API-Key': 'your_api_key' }
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
  "gender": "woman|man",
  "user_identity": "woman|man|non-binary",
  "history_text": "...prior transcript...",
  "user_utterance": "hey—open spotify and queue my mix"
}
```

Cancel a turn

```json
{ "type": "cancel" }
```
- Shortcut: send the literal `__CANCEL__` string (configurable via `WS_CANCEL_SENTINEL`) when clients cannot emit JSON.
- Optional: include `"request_id"` to get it echoed back in the server’s `{"type":"done","cancelled":true}` acknowledgement.

Gracefully end a session

```json
{ "type": "end" }
```

- The literal `__END__` sentinel (configurable via `WS_END_SENTINEL`) is also accepted.
- The server responds with `{"type":"connection_closed","reason":"client_request"}` and closes the socket with code `1000`.

Keep the connection warm during long pauses

```json
{ "type": "ping" }
```

- Server replies with `{"type":"pong"}` and resets the idle timer (default idle timeout: 150 s, set via `WS_IDLE_TIMEOUT_S`).
- Incoming `{"type":"pong"}` frames are treated as no-ops so clients can mirror the heartbeat without extra logic.

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
- `{"cancel": true}` or `__CANCEL__` produce the same result.
- The server immediately aborts both chat and tool engines, stops streaming tokens, and sends `{"type":"done","cancelled":true}` (plus `request_id` when provided).

Automatic barge-in (recommended for Pipecat):

```json
{"type": "start", "session_id": "user123", "user_utterance": "new message"}
```

- New `start` messages automatically cancel any ongoing generation for that session
- Both chat and tool models are immediately aborted; new response begins streaming right away
- Always send either a new `start`, `cancel`, or `end` before disconnecting so the connection slot is returned without waiting for the idle watchdog (150 s, configurable).
- Idle sockets are closed with code `4000` (`WS_CLOSE_IDLE_CODE`); periodic `ping` frames keep the session alive indefinitely.

Response handling:
- Cancelled requests return: `{ "type": "done", "cancelled": true }`
- New requests stream normally with `token` messages

### Rate Limits

- **Per connection:** General messages and cancel messages are governed by rolling-window quotas. Configure them via `WS_MAX_MESSAGES_PER_WINDOW` / `WS_MESSAGE_WINDOW_SECONDS` and `WS_MAX_CANCELS_PER_WINDOW` / `WS_CANCEL_WINDOW_SECONDS`.
- **Per session:** Persona updates (`chat_prompt` messages) share their own rolling window controlled by `CHAT_PROMPT_UPDATE_MAX_PER_WINDOW` / `CHAT_PROMPT_UPDATE_WINDOW_SECONDS`.

The defaults are defined in `src/config/limits.py`, but every limiter can be tuned (or disabled by setting its limit or window to `0`) through environment variables. Sliding windows ensure slots free up gradually as time passes rather than on fixed minute boundaries.

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
scripts/main.sh awq <chat_model> <tool_model>
```

The pipeline writes `awq_metadata.json` and `README.md` into each quantized folder for transparency and reproducibility.

## Persona and History Behavior

- Chat prompts are rendered in ChatML, Mistral Instruct (mistral-common V7 template), or Llama-3 Instruct format based on the selected chat model (see `src/config/chat_prompt.py`)
- Prefix caching reuses any repeated spans within the process. If you swap persona but keep the history bytes identical, history KV stays hot.
- To guarantee a hit before speaking, send a `warm_persona` upfront.

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


