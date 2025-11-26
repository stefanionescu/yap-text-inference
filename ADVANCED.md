# Yap Text Inference Advanced Guide

This document covers advanced operations, configuration, and deep-dive details.

## Contents

- [Authentication Coverage](#authentication-coverage)
- [Log Rotation](#log-rotation)
- [Viewing Logs](#viewing-logs)
- [Linting](#linting)
- [API — WebSocket `/ws`](#api--websocket-ws)
  - [WebSocket Protocol Highlights](#websocket-protocol-highlights)
  - [Connection Lifecycle](#connection-lifecycle)
  - [Authentication Methods](#authentication-methods)
  - [Connection Limit Handling](#connection-limit-handling)
  - [Messages You Send](#messages-you-send)
  - [What You Receive](#what-you-receive)
  - [Barge-In and Cancellation](#barge-in-and-cancellation)
- [Quantization Notes](#quantization-notes)
  - [Pushing AWQ Exports to Hugging Face](#pushing-awq-exports-to-hugging-face)
- [Server Status and Capacity](#server-status-and-capacity)
- [Persona and History Behavior](#persona-and-history-behavior)
- [GPU Memory Fractions](#gpu-memory-fractions)

## Authentication Coverage

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

## Viewing Logs

All deployment and server logs are unified in a single `server.log` file.

```bash
# Follow logs in real-time (deployment + server activity)
tail -f server.log

# View the last N lines (e.g., last 200 lines)
tail -n 200 server.log

# View the first N lines (e.g., first 100 lines)
head -n 100 server.log
```

Note: `scripts/main.sh` auto-tails all logs by default. Ctrl+C detaches from tail without stopping the deployment.

## Linting

Create/activate a virtualenv, install runtime + dev deps, then run the integrated lint script:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
bash scripts/lint.sh
```

`scripts/lint.sh` runs Ruff across `src` and `test`, then ShellCheck over every tracked `*.sh`, exiting non-zero if anything fails.

## API — WebSocket `/ws`

The server maintains persistent WebSocket connections with session-based user assignment. Each client provides a `session_id` for user identification, and the connection can handle multiple requests over time with automatic interruption support.

### WebSocket Protocol Highlights

- **Start**: `{"type":"start", ...}` begins/queues a turn. Sending another `start` automatically cancels the previous turn for that session (barge-in).
- **Sampling overrides (optional)**: Include a `sampling` object inside the `start` payload to override chat decoding knobs per session, for example:
  `{"type":"start", "...": "...", "sampling":{"temperature":0.8,"top_p":0.85}}`. Supported keys are `temperature`, `top_p`, `top_k`, `min_p`, `repetition_penalty`, `presence_penalty`, `frequency_penalty`, and `sanitize_output` (boolean, default `true`). Any omitted key falls back to the server defaults in `src/config/sampling.py`. Set `sanitize_output` to `false` to receive raw LLM output without cleanup.
- **Cancel**: `{"type":"cancel"}` (or the literal sentinel `__CANCEL__`) immediately stops both chat and tool engines. The server replies with `{"type":"done","cancelled":true}` (echoing `request_id` when provided).
- **Client end**: `{"type":"end"}` (or the sentinel `__END__`) requests a clean shutdown. The server responds with `{"type":"connection_closed","reason":"client_request"}` before closing with code `1000`.
- **Heartbeat**: `{"type":"ping"}` keeps the socket active during long pauses. The server answers with `{"type":"pong"}`; receiving `{"type":"pong"}` from clients is treated as a no-op. Every ping/ack resets the idle timer.
- **Idle timeout**: Connections with no activity for 150 s (configurable via `WS_IDLE_TIMEOUT_S`) are closed with code `4000`. Send periodic pings or requests to stay connected longer.
- **Sentinel shortcuts**: The default `WS_END_SENTINEL="__END__"` / `WS_CANCEL_SENTINEL="__CANCEL__"` are accepted as raw text frames for clients that can't emit JSON.
- **Rate limits**: Rolling-window quotas for both general messages and cancel messages are enforced per connection, while persona updates are limited per session. Tune the behavior via `WS_MAX_MESSAGES_PER_WINDOW` / `WS_MESSAGE_WINDOW_SECONDS`, `WS_MAX_CANCELS_PER_WINDOW` / `WS_CANCEL_WINDOW_SECONDS`, and `CHAT_PROMPT_UPDATE_MAX_PER_WINDOW` / `CHAT_PROMPT_UPDATE_WINDOW_SECONDS` (see `src/config/limits.py` for defaults).
- **Capacity guard**: Admissions are gated by a global semaphore (configurable via `MAX_CONCURRENT_CONNECTIONS` and `WS_HANDSHAKE_ACQUIRE_TIMEOUT_S`). When the server returns `server_at_capacity`, retry with backoff.
- **Done frame contract**: Every turn ends with `{"type":"done","usage":{...}}` when it succeeds, or `{"type":"done","cancelled":true}` when it's interrupted (explicit cancel or barge-in).

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
- Pre-quantized models: Point `CHAT_MODEL` / `TOOL_MODEL` at pre-quantized AWQ or W4A16 repos; Yap skips quantization automatically
- Smart detection: Any repo name containing `awq`, `w4a16`, `nvfp4`, `compressed-tensors`, or `autoround` is treated as 4-bit and run directly
- The tool model (`MadeAgents/Hammer2.1-1.5b` or `-3b`) is also quantized to 4-bit AWQ on load for consistency (local mode)
- AWQ requires additional wheels (installed automatically via `requirements.txt`)
- Qwen2/Qwen3 and Mistral 3 checkpoints automatically fall back to AutoAWQ 0.2.9 when quantized because llmcompressor cannot reliably trace their hybrid forward graphs yet. Metadata/readmes flag the backend so downstream consumers know whether AutoAWQ or llmcompressor produced the export.
- Auth for private/gated repos: Set `HUGGINGFACE_HUB_TOKEN` or `HF_TOKEN`
- Cache location: This repo standardizes on `HF_HOME` (override with `export HF_HOME=/path/to/cache`)
- Networking: For script-based deployments, HF transfer acceleration is disabled by default; opt in with `HF_HUB_ENABLE_HF_TRANSFER=1` when supported

### Pushing AWQ Exports to Hugging Face

When `QUANTIZATION=awq`, the deployment pipeline can upload the freshly quantized folders to the Hugging Face Hub. Uploads are opt-in and controlled via environment variables shared by both the full deployer (`scripts/main.sh`) and the restart helper (`scripts/restart.sh --push-awq ...`).

**Required when `HF_AWQ_PUSH=1`:**
- `HF_TOKEN` (or `HUGGINGFACE_HUB_TOKEN`) with write access
- `HF_AWQ_CHAT_REPO` pointing to your chat AWQ repo whenever chat/both are deployed
- `HF_AWQ_TOOL_REPO` pointing to your tool AWQ repo whenever tool/both are deployed

**Optional tuning (defaults shown below):**
- `HF_AWQ_BRANCH` – upload branch (default `main`)
- `HF_AWQ_PRIVATE` – create repo as private (`1`) or public (`0`)
- `HF_AWQ_ALLOW_CREATE` – auto-create repo (`1`) or require it to exist (`0`)
- `HF_AWQ_COMMIT_MSG_CHAT` / `HF_AWQ_COMMIT_MSG_TOOL` – commit message overrides

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

# re-upload cached AWQ exports during a restart (no full redeploy needed)
bash scripts/restart.sh --push-awq [deploy_mode] [--reset-models]
```

The pipeline writes `awq_metadata.json` and `README.md` into each quantized folder for transparency and reproducibility.

## Server Status and Capacity

```bash
# With API key (required)
curl -H "X-API-Key: your_api_key" http://127.0.0.1:8000/status

# Via query parameter
curl "http://127.0.0.1:8000/status?api_key=your_api_key"
```

Returns server status and connection capacity information, including current active connections and limits.

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


