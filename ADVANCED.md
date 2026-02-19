# Yap Text Inference Advanced Guide

This document covers advanced operations, configuration, and deep-dive details for both vLLM and TensorRT-LLM engines.

## Contents

- [Authentication Coverage](#authentication-coverage)
- [Telemetry](#telemetry)
- [Inference Engine Configuration](#inference-engine-configuration)
  - [Engine Selection](#engine-selection)
  - [vLLM Configuration](#vllm-configuration)
  - [TensorRT-LLM Configuration](#tensorrt-llm-configuration)
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
  - [Rate Limits](#rate-limits)
- [Quantization Notes](#quantization-notes)
  - [vLLM Quantization Details](#vllm-quantization-details)
  - [TensorRT-LLM Quantization Details](#tensorrt-llm-quantization-details)
  - [Pushing Quantized Exports to Hugging Face](#pushing-quantized-exports-to-hugging-face)
- [Test Clients](#test-clients)
  - [Warmup Test Client](#warmup-test-client)
  - [Interactive Live Client](#interactive-live-client)
  - [Conversation History Test](#conversation-history-test)
  - [Vision / Toolcall Test](#vision--toolcall-test)
  - [Tool Regression Test](#tool-regression-test)
  - [Benchmark Client](#benchmark-client)
  - [History Recall Test](#history-recall-test)
  - [Latency Metrics in Multi-Turn Tests](#latency-metrics-in-multi-turn-tests)
- [Persona and History Behavior](#persona-and-history-behavior)
- [GPU Memory Fractions](#gpu-memory-fractions)
- [Known Issues](#known-issues)
  - [TRT-LLM Python Version Mismatch](#trt-llm-python-version-mismatch)
  - [CUDA 13.0 Requirement](#cuda-130-requirement)
  - [Base Docker Image Selection](#base-docker-image-selection)
  - [CUDA Device Unavailable](#cuda-device-unavailable)

## Authentication Coverage

- `/healthz` – No authentication required
- `/ws` – Requires API key

## Telemetry

The server supports optional production observability via **Sentry** (error tracking) and **Axiom** (traces + metrics via OpenTelemetry). Both are disabled by default — the service runs identically when credentials are absent, with zero overhead (no-op meters/tracers).

### Enabling Telemetry

Set the relevant environment variables to activate each backend:

| Backend | Enable by setting | What you get |
|---------|-------------------|--------------|
| Sentry | `SENTRY_DSN` | Error reports with `session_id`/`request_id`/`client_id` tags, rate-limited per error class (10 s) |
| Axiom | `AXIOM_API_TOKEN` | OpenTelemetry traces (session → request → generation spans) and metrics exported via OTLP/HTTP |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SENTRY_DSN` | _(empty)_ | Sentry DSN. Leave empty to disable. |
| `SENTRY_ENVIRONMENT` | `production` | Sentry environment tag |
| `SENTRY_RELEASE` | _(empty)_ | Sentry release tag |
| `SENTRY_SAMPLE_RATE` | `1.0` | Error event sample rate (0.0–1.0) |
| `AXIOM_API_TOKEN` | _(empty)_ | Axiom API token. Leave empty to disable. |
| `AXIOM_DATASET` | `text-inference-api` | Axiom dataset name |
| `AXIOM_ENVIRONMENT` | `production` | Deployment environment for traces/metrics |
| `CLOUD_PLATFORM` | _(empty)_ | Fleet tag (`runpod`, `lambda-labs`, `aws`, `hetzner`, etc.) |
| `OTEL_SERVICE_NAME` | `yap-text-inference-api` | OTel service name on every span and metric |
| `OTEL_TRACES_EXPORT_INTERVAL_MS` | `5000` | Span batch flush interval |
| `OTEL_METRICS_EXPORT_INTERVAL_MS` | `15000` | Metric export interval |
| `OTEL_TRACES_BATCH_SIZE` | `512` | Max spans per export batch |

### Staging vs Production

Set `SENTRY_ENVIRONMENT` and `AXIOM_ENVIRONMENT` to `staging` for non-production deployments. All events and metrics are tagged with the environment value.

### Metrics Reference

**Histograms:**

| Metric | Unit | Description |
|--------|------|-------------|
| `text_inference.ttft` | s | Time to first token |
| `text_inference.request_latency` | s | End-to-end request latency |
| `text_inference.token_latency` | s | Inter-token arrival time |
| `text_inference.connection_duration` | s | WebSocket session duration |
| `text_inference.connection_semaphore_wait` | s | Slot acquisition wait |
| `text_inference.prompt_tokens` | {token} | Input prompt token count |
| `text_inference.completion_tokens` | {token} | Output completion token count |
| `text_inference.generations_per_session` | {request} | Requests per session |
| `text_inference.startup_duration` | s | Server startup time |
| `text_inference.tool_classification_latency` | s | Tool model inference time |

**Counters:**

| Metric | Unit | Description |
|--------|------|-------------|
| `text_inference.requests_total` | {request} | Total requests (status dimension) |
| `text_inference.tokens_generated_total` | {token} | Total tokens generated |
| `text_inference.prompt_tokens_total` | {token} | Total prompt tokens processed |
| `text_inference.connections_rejected_total` | {connection} | Rejected at capacity |
| `text_inference.session_churn_total` | {session} | Completed sessions |
| `text_inference.cancellation_total` | {request} | Client cancellations |
| `text_inference.errors_total` | {error} | Unhandled errors (error.type dimension) |
| `text_inference.timeout_disconnects_total` | {connection} | Idle timeout disconnects |
| `text_inference.rate_limit_violations_total` | {violation} | Rate limit hits |
| `text_inference.tool_classifications_total` | {classification} | Tool model calls |
| `text_inference.cache_resets_total` | {reset} | vLLM cache resets |

**Gauges:**

| Metric | Unit | Description |
|--------|------|-------------|
| `text_inference.active_connections` | {connection} | Current WebSocket connections |
| `text_inference.active_generations` | {generation} | Currently running generations |

**GPU Observables (multi-device):**

| Metric | Unit | Description |
|--------|------|-------------|
| `text_inference.gpu.memory_used` | By | GPU memory in use |
| `text_inference.gpu.memory_free` | By | GPU memory available |
| `text_inference.gpu.memory_total` | By | Total GPU memory |
| `text_inference.gpu.utilization` | % | GPU compute utilization |

GPU metrics are reported per device with a `gpu.device.id` attribute. On CPU-only machines these observables return empty (no errors).

## Inference Engine Configuration

### Engine Selection

The server supports two inference engines selected at deployment time:

| Environment Variable | CLI Flag | Default |
|---------------------|----------|---------|
| `INFERENCE_ENGINE=trt` | `--trt` | **Yes** |
| `INFERENCE_ENGINE=vllm` | `--vllm` | No |

Switching engines requires a restart with environment wipe:

```bash
# Switch from TRT to vLLM (triggers full wipe)
bash scripts/restart.sh --vllm both

# Or via main.sh
bash scripts/main.sh --vllm 4bit <chat_model> <tool_model>
```

### vLLM Configuration

vLLM-specific environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_USE_V1` | `1` | Enable vLLM V1 engine |
| `VLLM_ATTENTION_BACKEND` | auto | Force attention backend (e.g., `FLASHINFER`, `XFORMERS`) |
| `ENFORCE_EAGER` | `0` | Disable CUDA graphs for debugging |
| `KV_DTYPE` | auto | KV cache dtype (`auto`, `fp8`, `int8`) |
| `AWQ_CACHE_DIR` | `.awq` | Local cache for AWQ exports |

**Cache Management:**
- vLLM resets prefix caches periodically to prevent fragmentation
- Configure interval with `CACHE_RESET_INTERVAL_SECONDS` (default: 600)

### TensorRT-LLM Configuration

TRT-LLM-specific environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TRT_ENGINE_DIR` | — | Path to compiled TRT engine directory |
| `TRT_CHECKPOINT_DIR` | — | Path to quantized checkpoint |
| `TRT_REPO_DIR` | `.trtllm-repo` | TRT-LLM repo clone for quantization scripts |
| `TRT_MAX_BATCH_SIZE` | **Required** | Max batch size baked into engine (see below) |
| `TRT_BATCH_SIZE` | Engine max | Runtime batch size override (optional) |
| `TRT_MAX_INPUT_LEN` | `CHAT_MAX_LEN` (5025) | Maximum input token length |
| `TRT_MAX_OUTPUT_LEN` | `CHAT_MAX_OUT` (150) | Maximum output token length |
| `TRT_DTYPE` | `float16` | Compute precision |
| `TRT_KV_FREE_GPU_FRAC` | `CHAT_GPU_FRAC` | GPU memory fraction for KV cache |

**Batch Size Configuration:**

TRT-LLM engines have `max_batch_size` baked in at build time. This is not the same as `MAX_CONCURRENT_CONNECTIONS`.

| Variable | When Required | Description |
|----------|---------------|-------------|
| `TRT_MAX_BATCH_SIZE` | Engine build | **Required** when quantizing or building from a TRT checkpoint. Baked into the compiled engine. |
| `TRT_BATCH_SIZE` | Runtime | **Optional** override for runtime batch size. Must be ≤ engine's baked-in max. |

**When is `TRT_MAX_BATCH_SIZE` required?**

- Fresh quantization (on-the-fly): Yes
- Pre-quantized TRT checkpoint models: Yes (engine must still be built from checkpoint)
- Pre-built engine via `TRT_ENGINE_DIR`: No (already baked in)

**Example:**

```bash
# Fresh quantization with explicit batch size
export TRT_MAX_BATCH_SIZE=32
bash scripts/main.sh --trt 4bit SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent

# Runtime with lower batch size (optional, must be <= 32)
export TRT_BATCH_SIZE=16
bash scripts/main.sh --trt 4bit <pre-built-engine-model> <tool_model>
```

The server validates that `TRT_BATCH_SIZE` ≤ engine's max at startup.

**AWQ Quantization Tuning:**

| Variable | Default | Description |
|----------|---------|-------------|
| `TRT_AWQ_BLOCK_SIZE` | `128` | AWQ quantization group size |
| `TRT_CALIB_SIZE` | `64` | Number of calibration samples |
| `TRT_CALIB_SEQLEN` | `CHAT_MAX_LEN + CHAT_MAX_OUT` | Calibration sequence length |
| `TRT_CALIB_BATCH_SIZE` | `16` | Batch size for AWQ calibration |

**8-bit Format Selection:**

TRT-LLM auto-selects the 8-bit format based on GPU architecture:

| GPU | SM Arch | 8-bit Format |
|-----|---------|--------------|
| H100 | sm90 | FP8 |
| L40S, RTX 4090 | sm89 | FP8 |
| A100 | sm80 | INT8-SQ (SmoothQuant) |

Override with `QUANTIZATION=fp8` or `QUANTIZATION=int8_sq`.

**MoE Model Support:**

MoE models (e.g., Qwen3-30B-A3B) are auto-detected by name patterns (`-aXb`, `moe`, `mixtral`, etc.) and use the same quantization as dense models.

**Engine Build Metadata:**

After building, metadata is recorded to `{engine_dir}/build_metadata.json`.

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

Use the repo virtualenv. If it doesn't exist, run `bash scripts/steps/03_install_deps.sh` first:

```bash
# ensure you're inside the repo venv
bash scripts/activate.sh
pip install -r requirements-dev.txt
bash scripts/lint.sh
# exit the subshell when finished
```

`scripts/lint.sh` runs:
- isort (import ordering)
- Ruff format + lint
- import-linter contracts
- import cycle detection (hard-fail on cycles)
- mypy (when installed)
- custom repo lint checks, including:
  - runtime file length limits (300 LOC; `src/**/*.py`, `scripts/**/*.sh`, `docker/**/*.sh`)
  - runtime Python function length limits (60 LOC; `src/**/*.py`)
  - one top-level class per runtime Python file (`src/**/*.py`) (dataclasses exempt)
  - no lazy singleton runtime patterns (`src/**/*.py`)
  - no lazy module loading/export patterns (`src/**/*.py`; no `__getattr__` lazy exports or `importlib.import_module` indirection)
  - no legacy/backward-compatibility markers in runtime orchestration modules
  - Docker ignore policy from `linting/policy.toml` (engine-local mode: only `docker/vllm/.dockerignore` and `docker/trt/.dockerignore` are allowed)
  - `__all__` must appear at module bottom (`src/**/*.py`)
  - no single-file folders in `src/` (promotes flat module layout)
  - no module-name prefix collisions (`src/**/*.py`)
  - no inline Python in shell scripts (`scripts/**/*.sh`, `docker/**/*.sh`)
- ShellCheck (and shfmt checks when available)

## API — WebSocket `/ws`

The server uses persistent WebSocket connections. Each client provides a `session_id`, and a connection can handle multiple requests with automatic interruption support.

### WebSocket Protocol Highlights

All client messages use a standard envelope:

```json
{
  "type": "...",
  "session_id": "<stable-per-user uuid>",
  "request_id": "<per-request uuid>",
  "payload": { ... }
}
```

Server responses use the same envelope and echo `session_id` / `request_id`.

- **Start**: `type:"start"` begins/queues a turn. Sending another `start` automatically cancels the previous turn for that session (barge-in).
- **Sampling overrides (optional)**: Include a `sampling` object inside the `start` payload to override chat decoding knobs per session, for example:
  `{"type":"start", "...": "...", "payload":{"sampling":{"temperature":0.8,"top_p":0.85}}}`. Supported keys are `temperature`, `top_p`, `top_k`, `min_p`, `repetition_penalty`, `presence_penalty`, `frequency_penalty`, and `sanitize_output` (boolean, default `true`). Any omitted key falls back to the server defaults in `src/config/sampling.py`. Set `sanitize_output` to `false` to receive raw LLM output without cleanup.
- **Cancel**: `type:"cancel"` with an empty payload (or optional `{"reason":"client_request"}`) immediately stops both chat and tool engines. The server replies with `type:"cancelled"` and stops streaming.
- **Client end**: `type:"end"` requests a clean shutdown. The server responds with `type:"session_end"` before closing with code `1000`.
- **Heartbeat**: `type:"ping"` keeps the socket active during long pauses. The server answers with `type:"pong"`; receiving `type:"pong"` from clients is treated as a no-op. Every ping/ack resets the idle timer.
- **Idle timeout**: Connections with no activity for 150 s (configurable via `WS_IDLE_TIMEOUT_S`) are closed with code `4000`. Send periodic pings or requests to stay connected longer.
- **Rate limits**: Rolling-window quotas for both general messages and cancel messages are enforced per connection. Tune the behavior via `WS_MAX_MESSAGES_PER_WINDOW` / `WS_MESSAGE_WINDOW_SECONDS` and `WS_MAX_CANCELS_PER_WINDOW` / `WS_CANCEL_WINDOW_SECONDS` (see `src/config/limits.py` for defaults).
- **Connection limit**: New connections are limited by `MAX_CONCURRENT_CONNECTIONS`. When the server returns `server_at_capacity`, retry with backoff.
- **Done frame**: Every successful turn ends with `type:"done"` and `payload.usage`. Cancelled turns return `type:"cancelled"`.

### Connection Lifecycle
1. Client connects to `ws://server:8000/ws?api_key=your_key`
2. Client sends `start` message with `session_id`
3. Connection stays open for multiple requests
4. Session state (persona, settings) persists across requests
5. New `start` messages cancel any in-progress request (barge-in)

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
- If at capacity, connection is rejected with `server_at_capacity`
- Retry with exponential backoff

### Messages You Send

Start a turn:

```json
{
  "type": "start",
  "session_id": "<stable-per-user uuid>",
  "request_id": "<uuid per turn>",
  "payload": {
    "chat_prompt": "...full system prompt for the assistant...",
    "personality": "savage|flirty|...",
    "gender": "female|male",
    "history": [
      {"role": "user", "content": "previous message"},
      {"role": "assistant", "content": "previous reply"}
    ],
    "user_utterance": "hey—open spotify and queue my mix"
  }
}
```

Cancel a turn:

```json
{
  "type": "cancel",
  "session_id": "<stable-per-user uuid>",
  "request_id": "<uuid per turn>",
  "payload": { "reason": "client_request" }
}
```
- The `payload` may be empty (`{}`) if you don't want to include a reason.

Gracefully end a session:

```json
{
  "type": "end",
  "session_id": "<stable-per-user uuid>",
  "request_id": "<uuid per turn>",
  "payload": {}
}
```

- The server responds with a `session_end` message and closes the socket with code `1000`.

Keep the connection warm during long pauses

```json
{
  "type": "ping",
  "session_id": "<stable-per-user uuid>",
  "request_id": "<uuid per ping>",
  "payload": {}
}
```

Continue an existing session (no history/persona re-send):

```json
{
  "type": "message",
  "session_id": "<stable-per-user uuid>",
  "request_id": "<uuid per turn>",
  "payload": {
    "user_utterance": "what about after that?",
    "sampling": { "temperature": 0.9 }
  }
}
```

- Requires a prior `start` for the same `session_id` — persona, history, and chat prompt are reused from the session.
- `sampling` is optional and overrides the session's chat sampling parameters.

Continue after external screen analysis (bypasses tool routing):

```json
{
  "type": "followup",
  "session_id": "<stable-per-user uuid>",
  "request_id": "<uuid per turn>",
  "payload": {
    "analysis_text": "The screen shows a Spotify queue with three tracks..."
  }
}
```

- Requires a prior `start` with `chat_prompt` set and a chat-model deployment.
- The server prepends a configurable prefix to the analysis text, appends it to history, and streams a chat-only response.

- Server replies with `{"type":"pong", ...}` (same envelope, empty payload) and resets the idle timer (default idle timeout: 150s, set via `WS_IDLE_TIMEOUT_S`).
- Incoming `{"type":"pong"}` frames are treated as no-ops so clients can mirror the heartbeat without extra logic.

### What You Receive

Authentication errors

```json
{
  "type": "error",
  "session_id": "unknown",
  "request_id": "unknown",
  "payload": {
    "code": "authentication_failed",
    "message": "Authentication required. Provide valid API key via 'api_key' query parameter or 'X-API-Key' header."
  }
}
```

Capacity errors

```json
{
  "type": "error",
  "session_id": "unknown",
  "request_id": "unknown",
  "payload": {
    "code": "server_at_capacity",
    "message": "Server cannot accept new connections. Please try again later."
  }
}
```

Tool-call decision

```json
{
  "type": "toolcall",
  "session_id": "<stable-per-user uuid>",
  "request_id": "<uuid per turn>",
  "payload": { "status": "yes", "raw": "..." }
}
{
  "type": "toolcall",
  "session_id": "<stable-per-user uuid>",
  "request_id": "<uuid per turn>",
  "payload": { "status": "no", "raw": "..." }
}
```

In both-model deployments, chat tokens always stream after the toolcall decision (for both `"yes"` and `"no"`).

### Barge-In and Cancellation

Explicit cancellation:

```json
{
  "type": "cancel",
  "session_id": "<stable-per-user uuid>",
  "request_id": "<uuid per turn>",
  "payload": {}
}
```
- The server immediately aborts both chat and tool engines, stops streaming tokens, and sends `{"type":"cancelled", ...}`.

Automatic barge-in (recommended for Pipecat):

```json
{
  "type": "start",
  "session_id": "user123",
  "request_id": "req-456",
  "payload": { "user_utterance": "new message" }
}
```

- New `start` messages automatically cancel any ongoing generation for that session
- Both chat and tool models are immediately aborted; new response begins streaming right away
- Always send either a new `start`, `cancel`, or `end` before disconnecting so the connection slot is returned without waiting for the idle watchdog (150 s, configurable).
- Idle sockets are closed with code `4000` (`WS_CLOSE_IDLE_CODE`); periodic `ping` frames keep the session alive indefinitely.

Response handling:
- Cancelled requests return: `{ "type": "cancelled", ... }`
- New requests stream normally with `token` messages

### Rate Limits

- **Per connection:** Messages and cancels have rate limits. Configure via `WS_MAX_MESSAGES_PER_WINDOW` / `WS_MESSAGE_WINDOW_SECONDS` and `WS_MAX_CANCELS_PER_WINDOW` / `WS_CANCEL_WINDOW_SECONDS`.
- **Per session:** Persona updates are not supported mid-session; the system prompt defined in the initial `start` message remains fixed.

Defaults are in `src/config/limits.py`. Set limit or window to `0` to disable.

## Quantization Notes

### vLLM Quantization Details

vLLM supports multiple quantization backends:

| Mode | Backend | Notes |
|------|---------|-------|
| `4bit` / `awq` | llmcompressor + vLLM | All models (including Qwen) |
| `gptq` / `gptq_marlin` | vLLM GPTQ | For pre-quantized GPTQ repos |
| `8bit` / `fp8` | vLLM FP8 | L40S/H100 native |
| `8bit` / `fp8` | vLLM FP8 (W8A16) | A100 emulated (FP8 weights, FP16 compute) |

**Local AWQ quantization tuning:**

| Variable | Default | Description |
|----------|---------|-------------|
| `AWQ_CALIB_DATASET` | `open_platypus` | Calibration dataset |
| `AWQ_NSAMPLES` | `64` | Number of calibration samples |
| `AWQ_SEQLEN` | `2048` | Calibration sequence length |

**Pre-quantized model detection:**
- Any repo name containing `awq`, `w4a16`, `compressed-tensors`, or `autoround` is treated as 4-bit
- Any repo name containing `gptq` is treated as GPTQ
- Tool models are always run in float precision (never quantized)

### TensorRT-LLM Quantization Details

TRT-LLM uses NVIDIA's quantization pipeline with a two-stage process:

1. **Quantization**: Creates a checkpoint with quantized weights
2. **Engine Build**: Compiles the checkpoint to a GPU-specific `.engine` file

**Quantization formats:**

| Mode | TRT Format | Model Type | GPU Support |
|------|------------|------------|-------------|
| `4bit` / `awq` | `int4_awq` | All models | All GPUs |
| `8bit` (H100/L40S) | `fp8` | All models | sm89, sm90 |
| `8bit` (A100) | `int8_sq` | All models | sm80 |

**MoE models:** MoE (Mixture of Experts) architectures follow the same INT4-AWQ path as dense models for 4-bit quantization.
**Engine portability:** TRT engines are GPU-architecture specific. An engine built on H100 will not run on A100 or L40S.

**Force rebuild:**

```bash
export FORCE_REBUILD=true
bash scripts/main.sh --trt 4bit <chat_model> <tool_model>
```

**Pre-quantized TRT models:**
- Repos containing both `trt` and `awq` in the name are detected as pre-quantized TRT checkpoints
- Repos containing `trt` plus any of `fp8`, `8bit`, `8-bit`, `int8`, or `int-8` are treated as prebuilt fp8/int8 checkpoints
- The server downloads the checkpoint and builds the engine locally

### Pushing Quantized Exports to Hugging Face

Pass `--push-quant` to `scripts/main.sh` or `scripts/restart.sh` to upload quantized models to HuggingFace. Without the flag, nothing is uploaded.

Uploads: vLLM AWQ/W4A16 exports or TRT-LLM checkpoints/engines (4-bit or 8-bit).

**Engine-only push (TRT):** Use `--push-engine` to push a locally-built TRT engine to an existing prequantized HuggingFace repo. This adds the compiled engine for your GPU architecture without re-uploading the checkpoint.

> **Note:** `--push-quant` and `--push-engine` are mutually exclusive.

**Required whenever `--push-quant` is present:**
- `HF_TOKEN` with write access
- `HF_PUSH_REPO_ID` – target Hugging Face repo (e.g., `your-org/model-awq`)

**Optional:**
- `HF_PUSH_PRIVATE` – `1` for private repo (default), `0` for public

Repos are auto-created if they don't exist.

**Examples:**

```bash
export HF_TOKEN="hf_your_api_token"
export HF_PUSH_REPO_ID="your-org/model-awq"  # repo name is arbitrary
export HF_PUSH_PRIVATE=1  # optional, default is private

# vLLM: Full deployment with HF push (AWQ/W4A16 export)
bash scripts/main.sh --vllm 4bit <chat_model> <tool_model> --push-quant

# TRT: Full deployment with HF push (4-bit export)
bash scripts/main.sh --trt 4bit <chat_model> <tool_model> --push-quant

# TRT: Upload an 8-bit fp8/int8_sq export
bash scripts/main.sh --trt 8bit <chat_model> <tool_model> --push-quant

# Restart with quantization and push (either engine)
bash scripts/restart.sh chat --push-quant --chat-model <model> --chat-quant 4bit

# Restart workflow pushing a cached 8-bit TRT build
bash scripts/restart.sh chat --push-quant --chat-model <model> --chat-quant 8bit
```

The pipeline writes metadata (`awq_metadata.json` or `build_metadata.json`) and `README.md` to each quantized folder.

## Test Clients

All test clients run against the WebSocket endpoint. Run them via `scripts/activate.sh` (e.g., `bash scripts/activate.sh python3 tests/e2e/warmup.py`) or source `.venv-local/bin/activate` for unit testing.

> **Note:** Test clients always send a chat prompt. In tool-only deployments, the server ignores it automatically.

### Unit Tests

Run deterministic CPU-only unit tests for sanitizer behavior, token accounting, history trimming, start-message metrics, and websocket helper logic:

```bash
python -m pytest -q \
  tests/integration/sanitizer.py \
  tests/unit/history/start_history.py \
  tests/unit/history/history_accounting.py \
  tests/unit/tokens/token_accounting.py \
  tests/unit/history/history_parsing.py \
  tests/unit/tokens/prefix_accounting.py \
  tests/unit/websocket/ws_helpers.py
```

### Warmup Test Client

```bash
# run these after entering the venv via 'bash scripts/activate.sh'
python3 tests/e2e/warmup.py
python3 tests/e2e/warmup.py "who was Columbus?"
python3 tests/e2e/warmup.py --gender male --personality flirty "hello there"
```


Environment overrides honored by the client:
- `SERVER_WS_URL` (default `ws://127.0.0.1:8000/ws`)
- `GENDER` (aliases `woman|man`)
- `PERSONALITY` (default `wholesome`)
- `RECV_TIMEOUT_SEC` (default `60`)

Example:

```bash
SERVER_WS_URL=ws://127.0.0.1:8000/ws \
RECV_TIMEOUT_SEC=120 \
python3 tests/e2e/warmup.py --gender female --personality savage "hey there"
```

Append `--double-ttfb` to send two identical requests back-to-back and compare cold vs warm latency.

### Interactive Live Client

```bash
# run inside the scripts/activate.sh environment
TEXT_API_KEY=your_api_key python3 tests/e2e/live.py \
  --server ws://127.0.0.1:8000 \
  --persona default_live_persona
```

Flags:
- `--server`: explicit URL (falls back to `SERVER_WS_URL`, appends `/ws` if missing)
- `--api-key`: override `TEXT_API_KEY`
- `--persona/-p`: persona key from `tests/prompts/detailed.py` (defaults to `anna_flirty`)
- `--timeout`: receive timeout in seconds (default 60)
- `--warm`: start with pre-built conversation history for testing recall
- positional text: optional opener message

### Conversation History Test

```bash
# run inside the scripts/activate.sh environment
TEXT_API_KEY=your_api_key python3 tests/e2e/conversation.py --server ws://127.0.0.1:8000
```

Streams a 10-turn script to test history eviction and KV-cache reuse.

### Vision / Toolcall Test

```bash
TEXT_API_KEY=your_api_key python3 tests/e2e/vision.py
```

Tests that toolcall decisions fire before chat streaming.

### Tool Regression Test

```bash
TEXT_API_KEY=your_api_key python3 tests/e2e/tool.py \
  --server ws://127.0.0.1:8000/ws \
  --timeout 5 \
  --concurrency 4 \
  --limit 50 \
  --max-steps 20
```

- `--timeout`: wait per tool decision (default 5 s)
- `--concurrency`: parallel cases if the tool engine has capacity
- `--limit`: cap the number of replayed cases for faster smoke runs

### Benchmark Client

```bash
# run inside the scripts/activate.sh environment
python3 tests/e2e/bench.py -n 32 -c 8
python3 tests/e2e/bench.py --gender female --personality flirty "who was Columbus?"
python3 tests/e2e/bench.py --server ws://127.0.0.1:8000/ws -n 100 -c 20 --timeout 180
```

Reports p50/p95 latencies under concurrent load.

Pass `--double-ttfb` to run two sequential transactions per connection and compare cold vs warm latency.

### History Recall Test

```bash
# run inside the scripts/activate.sh environment
TEXT_API_KEY=your_api_key python3 tests/e2e/history.py
TEXT_API_KEY=your_api_key python3 tests/e2e/history.py --gender male --personality flirty
TEXT_API_KEY=your_api_key python3 tests/e2e/history.py --temperature 0.8 --top_p 0.9
```

Connects with a pre-built conversation history, then sends follow-up messages to test the assistant's recall of earlier exchanges. Tracks TTFB for each response and prints summary statistics (p50, p90, p95). Useful for validating prefix caching and KV cache reuse.

**Benchmark mode:** pass `--bench` to run concurrent connections with warm history:

```bash
# 8 connections, 4 concurrent (defaults)
TEXT_API_KEY=your_api_key python3 tests/e2e/history.py --bench

# Custom load: 16 connections, 8 concurrent
TEXT_API_KEY=your_api_key python3 tests/e2e/history.py --bench -n 16 -c 8

# With custom timeout
TEXT_API_KEY=your_api_key python3 tests/e2e/history.py --bench -n 32 -c 16 --timeout 300
```

Each connection starts with the full warm history and cycles through all recall messages. Output matches the benchmark client format with p50/p95 latencies.

### Cancel Regression Test

```bash
# run inside the scripts/activate.sh environment
TEXT_API_KEY=your_api_key python3 tests/integration/cancel.py
TEXT_API_KEY=your_api_key python3 tests/integration/cancel.py --clients 3 --cancel-delay 1.0 --drain-timeout 2.0
```

Validates cancel behavior and recovery:
- Cancels an in-flight response after receiving initial tokens
- Verifies no extra post-cancel stream frames are emitted
- Sends a recovery request and confirms the session continues normally

### Idle Timeout Test

```bash
# run inside the scripts/activate.sh environment
TEXT_API_KEY=your_api_key python3 tests/integration/idle.py
TEXT_API_KEY=your_api_key python3 tests/integration/idle.py --normal-wait 5 --idle-expect-seconds 150
```

Tests WebSocket idle timeout and connection lifecycle:
- **Normal close**: Opens a connection, waits, sends `end` frame, verifies clean shutdown
- **Idle timeout**: Opens a connection, stays idle, verifies server closes with code `4000`

Flags:
- `--normal-wait`: Seconds to keep connection open before sending end (default: 3)
- `--idle-expect-seconds`: Expected idle timeout from server (default: 150)
- `--idle-grace-seconds`: Buffer before failing the idle test (default: 15)

### Latency Metrics in Multi-Turn Tests

Multi-turn tests report latency statistics with the **first message excluded from averages and percentiles**.

The first message in a conversation includes prefill overhead for the system prompt, chat prompt, and any warm history. This makes it significantly slower than subsequent messages where the KV cache is already populated. To provide accurate steady-state latency metrics:

- **FIRST** row: Shows the first message latency separately (includes prefill overhead)
- **Remaining rows** (TTFB, 3-WORDS, SENTENCE): avg/p50/p90/p95 computed from messages 2+ only

Example output:
```
─────────────[ LATENCY SUMMARY ]─────────────
  FIRST  (includes prefill)  ttfb=679ms  3w=149ms  sent=670ms
      TTFB  avg=   110ms  p50=   109ms  p90=   128ms  p95=   141ms  (n=5)
   3-WORDS  avg=   155ms  p50=   152ms  p90=   169ms  p95=   185ms  (n=5)
  SENTENCE  avg=   450ms  p50=   411ms  p90=   670ms  p95=   892ms  (n=5)
```

This separation ensures the reported percentiles reflect real conversational latency after the initial prompt processing.

## Persona and History Behavior

- Chat prompts are rendered using each model's tokenizer
- **vLLM:** Prefix caching reuses repeated prompts automatically. Swapping the system prompt keeps history KV hot.
- **TensorRT-LLM:** Block reuse handles KV cache automatically.
- **Tool model context windows are model-aware by default:**
  - Longformer-based tool models: `1536` tokens
  - BERT/ModernBERT-based tool models: `512` tokens
  - You can override with `TOOL_MAX_LENGTH` and `TOOL_HISTORY_TOKENS`.
  - Effective tool history budget is clamped to the tool model's effective max sequence length.
- **Oversized latest user messages for tool routing are tail-truncated (keep end)** so the most recent part still reaches the tool model.

## Known Issues

### TRT-LLM Python Version Mismatch

TRT-LLM 1.2.0 claims Python 3.11 support but it doesn't work reliably. Use Python 3.10.

### CUDA 13.0 Requirement

TRT-LLM 1.2.0rc5 requires CUDA 13.0 and PyTorch 2.9.0. Use:
- `torch==2.9.0+cu130` with `--index-url https://download.pytorch.org/whl/cu130`
- `torchvision==0.24.0+cu130`

### Base Docker Image Selection

Installing OpenMPI packages can silently downgrade CUDA below 13.0, breaking TRT-LLM.

**Workarounds:**
1. Use a base image with CUDA 13.0 and proper apt pinning
2. Pin MPI versions via `MPI_VERSION_PIN` before bootstrap
3. Verify: `nvcc --version` should show 13.0+

### CUDA Device Unavailable

Torch logs `Device 0 seems unavailable` even though `nvidia-smi` shows the GPU.

Causes:
- Container mapped to wrong device node
- Stale GPU assignment or MIG mismatch
- GPU needs reset

Fixes:
- Restart container with `--gpus all` or specific UUID
- Switch to a different GPU
- Reset GPU: `nvidia-smi --gpu-reset -i 0`

## GPU Memory Fractions

- Single model: 90%
- Both models: 70% chat, 20% tool

Override:

```bash
export CHAT_GPU_FRAC=0.60
export TOOL_GPU_FRAC=0.25
bash scripts/stop.sh && bash scripts/main.sh --trt 4bit <chat_model> <tool_model>
```

**TRT-LLM:** `TRT_KV_FREE_GPU_FRAC` controls KV cache memory (defaults to `CHAT_GPU_FRAC`). Engine build uses `TRT_MAX_BATCH_SIZE` for KV cache slots.
