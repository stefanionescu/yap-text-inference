# Yap Text Inference Advanced Guide

This document covers advanced operations, configuration, and deep-dive details for both vLLM and TensorRT-LLM engines.

## Contents

- [Authentication Coverage](#authentication-coverage)
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
- [Persona and History Behavior](#persona-and-history-behavior)
- [GPU Memory Fractions](#gpu-memory-fractions)
- [Known Issues](#known-issues)
  - [TRT-LLM Python Version Mismatch](#trt-llm-python-version-mismatch)
  - [CUDA 13.0 Requirement](#cuda-130-requirement)
  - [Base Docker Image Selection](#base-docker-image-selection)

## Authentication Coverage

- `/healthz` – No authentication required
- `/ws` – Requires API key

## Inference Engine Configuration

### Engine Selection

Yap supports two inference engines selected at deployment time:

| Environment Variable | CLI Flag | Default |
|---------------------|----------|---------|
| `INFERENCE_ENGINE=trt` | `--trt` | **Yes** |
| `INFERENCE_ENGINE=vllm` | `--vllm` | No |

The engine is locked at startup. Switching engines requires a full restart with environment wipe:

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
| `VLLM_ATTENTION_BACKEND` | auto | Force attention backend (e.g., `FLASH_ATTN`, `FLASHINFER`) |
| `ENFORCE_EAGER` | `0` | Disable CUDA graphs for debugging |
| `VLLM_ALLOW_LONG_MAX_MODEL_LEN` | `1` | Allow context lengths beyond model config |
| `KV_DTYPE` | auto | KV cache dtype (`auto`, `fp8`, `int8`) |
| `AWQ_CACHE_DIR` | `.awq` | Local cache for AWQ exports |

**Cache Management:**
- vLLM periodically resets prefix and multimodal caches to prevent fragmentation
- Configure interval with `CACHE_RESET_INTERVAL_SECONDS` (default: 600)
- Force immediate reset via `reset_engine_caches()` API

### TensorRT-LLM Configuration

TRT-LLM-specific environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TRTLLM_ENGINE_DIR` | — | Path to compiled TRT engine directory |
| `TRT_CHECKPOINT_DIR` | — | Path to quantized checkpoint |
| `TRTLLM_REPO_DIR` | `.trtllm-repo` | TRT-LLM repo clone for quantization scripts |
| `TRT_MAX_BATCH_SIZE` | **Required** | Max batch size baked into engine (see below) |
| `TRT_BATCH_SIZE` | Engine max | Runtime batch size override (optional) |
| `TRT_MAX_INPUT_LEN` | `CHAT_MAX_LEN` (5525) | Maximum input token length |
| `TRT_MAX_OUTPUT_LEN` | `CHAT_MAX_OUT` (150) | Maximum output token length |
| `TRT_DTYPE` | `float16` | Compute precision |
| `TRT_KV_FREE_GPU_FRAC` | `CHAT_GPU_FRAC` | GPU memory fraction for KV cache |
| `TRT_KV_ENABLE_BLOCK_REUSE` | `0` | Enable KV block reuse (automatic) |

**Batch Size Configuration:**

TRT-LLM engines have a `max_batch_size` baked in at build time. This determines how many sequences can be batched together in a single forward pass—it is **not** the same as `MAX_CONCURRENT_CONNECTIONS` (WebSocket connections).

| Variable | When Required | Description |
|----------|---------------|-------------|
| `TRT_MAX_BATCH_SIZE` | Engine build | **Required** when quantizing or building from a TRT checkpoint. Baked into the compiled engine. |
| `TRT_BATCH_SIZE` | Runtime | **Optional** override for runtime batch size. Must be ≤ engine's baked-in max. |

**When is `TRT_MAX_BATCH_SIZE` required?**

- ✅ Fresh quantization (on-the-fly): Yes
- ✅ Pre-quantized TRT checkpoint models: Yes (engine must still be built from checkpoint)
- ❌ Pre-built engine via `TRTLLM_ENGINE_DIR`: No (already baked in)

**Example:**

```bash
# Fresh quantization with explicit batch size
export TRT_MAX_BATCH_SIZE=32
bash scripts/main.sh --trt 4bit SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent

# Runtime with lower batch size (optional, must be <= 32)
export TRT_BATCH_SIZE=16
bash scripts/main.sh --trt 4bit <pre-built-engine-model> <tool_model>
```

At runtime, the server validates that `TRT_BATCH_SIZE` ≤ engine's max and logs both values at startup.

**AWQ Quantization Tuning:**

| Variable | Default | Description |
|----------|---------|-------------|
| `TRT_AWQ_BLOCK_SIZE` | `128` | AWQ quantization group size |
| `TRT_CALIB_SIZE` | `64` | Number of calibration samples |
| `TRT_CALIB_SEQLEN` | `CHAT_MAX_LEN + CHAT_MAX_OUT` | Calibration sequence length |

**8-bit Format Selection:**

TRT-LLM auto-selects the 8-bit format based on GPU architecture:

| GPU | SM Arch | 8-bit Format |
|-----|---------|--------------|
| H100 | sm90 | FP8 |
| L40S, RTX 4090 | sm89 | FP8 |
| A100 | sm80 | INT8-SQ (SmoothQuant) |

Override with `QUANTIZATION=fp8` or `QUANTIZATION=int8_sq`.

**MoE Model Support:**

Mixture-of-Experts models (e.g., Qwen3-30B-A3B) are automatically detected by:
- Naming convention: `-aXb` suffix (e.g., `qwen3-30b-a3b`)
- Model type markers: `moe`, `mixtral`, `deepseek-v2/v3`

MoE models use `quantize_mixed_precision_moe.py` instead of the standard quantization script.

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

Create/activate a virtualenv, install runtime + dev deps, then run the integrated lint script:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
bash scripts/lint.sh
```

`scripts/lint.sh` runs Ruff across `src` and `tests`, then ShellCheck over every tracked `*.sh`, exiting non-zero if anything fails.

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
- Optional: include `"request_id"` to get it echoed back in the server's `{"type":"done","cancelled":true}` acknowledgement.

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

- Server replies with `{"type":"pong"}` and resets the idle timer (default idle timeout: 150 s, set via `WS_IDLE_TIMEOUT_S`).
- Incoming `{"type":"pong"}` frames are treated as no-ops so clients can mirror the heartbeat without extra logic.

Warm persona/history (cache priming; optional)

```json
{ "type": "warm_persona", "chat_prompt": "..." }
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
- Always send either a new `start`, `cancel`, or `end` before disconnecting so the connection slot is returned without waiting for the idle watchdog (150 s, configurable).
- Idle sockets are closed with code `4000` (`WS_CLOSE_IDLE_CODE`); periodic `ping` frames keep the session alive indefinitely.

Response handling:
- Cancelled requests return: `{ "type": "done", "cancelled": true }`
- New requests stream normally with `token` messages

### Rate Limits

- **Per connection:** General messages and cancel messages are governed by rolling-window quotas. Configure them via `WS_MAX_MESSAGES_PER_WINDOW` / `WS_MESSAGE_WINDOW_SECONDS` and `WS_MAX_CANCELS_PER_WINDOW` / `WS_CANCEL_WINDOW_SECONDS`.
- **Per session:** Persona updates (`chat_prompt` messages) share their own rolling window controlled by `CHAT_PROMPT_UPDATE_MAX_PER_WINDOW` / `CHAT_PROMPT_UPDATE_WINDOW_SECONDS`.

The defaults are defined in `src/config/limits.py`, but every limiter can be tuned (or disabled by setting its limit or window to `0`) through environment variables. Sliding windows ensure slots free up gradually as time passes rather than on fixed minute boundaries.

## Quantization Notes

### vLLM Quantization Details

vLLM supports multiple quantization backends:

| Mode | Backend | Notes |
|------|---------|-------|
| `4bit` / `awq` | llmcompressor + vLLM | Default for most models |
| `4bit` (Qwen/Mistral3) | AutoAWQ 0.2.9 | Fallback for hybrid architectures |
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
- Any repo name containing `awq`, `w4a16`, `nvfp4`, `compressed-tensors`, or `autoround` is treated as 4-bit
- Any repo name containing `gptq` is treated as GPTQ
- Tool models are always run in float precision (never quantized)

### TensorRT-LLM Quantization Details

TRT-LLM uses NVIDIA's quantization pipeline with a two-stage process:

1. **Quantization**: Creates a checkpoint with quantized weights
2. **Engine Build**: Compiles the checkpoint to a GPU-specific `.engine` file

**Quantization formats:**

| Mode | TRT Format | GPU Support |
|------|------------|-------------|
| `4bit` / `awq` | `int4_awq` | All GPUs |
| `8bit` (H100/L40S) | `fp8` | sm89, sm90 |
| `8bit` (A100) | `int8_sq` | sm80 |

**Engine portability:** TRT engines are GPU-architecture specific. An engine built on H100 will not run on A100 or L40S.

**Force rebuild:**

```bash
export FORCE_REBUILD=true
bash scripts/main.sh --trt 4bit <chat_model> <tool_model>
```

**Pre-quantized TRT models:**
- Repos containing both `trt` and `awq` in the name are detected as pre-quantized TRT checkpoints
- The server downloads the checkpoint and builds the engine locally

### Pushing Quantized Exports to Hugging Face

Uploads **only** happen when you pass `--push-quant` to the launcher you're using (`scripts/main.sh` or `scripts/restart.sh`). No flag, no upload—environment variables alone will never trigger a push.

When `--push-quant` is specified, the script validates required parameters **at the very beginning** (before any downloads or heavy operations). If validation fails, the script exits immediately with a clear error message.

**Required whenever `--push-quant` is present:**
- `HF_TOKEN` (or `HUGGINGFACE_HUB_TOKEN`) with write access
- `HF_PUSH_REPO_ID` – target Hugging Face repo (e.g., `your-org/model-awq`)

**Optional:**
- `HF_PUSH_PRIVATE` – `1` for private repo (default), `0` for public

Uploads always push to the `main` branch. Repos are auto-created if they don't exist.

**Example (both engines use the same params):**

```bash
export HF_TOKEN="hf_your_api_token"
export HF_PUSH_REPO_ID="your-org/model-awq"
export HF_PUSH_PRIVATE=1  # optional, default is private

# vLLM: Full deployment with HF push
bash scripts/main.sh --vllm 4bit <chat_model> <tool_model> --push-quant

# TRT: Full deployment with HF push
bash scripts/main.sh --trt 4bit <chat_model> <tool_model> --push-quant

# Restart with quantization and push (either engine)
bash scripts/restart.sh chat --push-quant --chat-model <model> --chat-quant 4bit
```

**Note:** The `--push-quant` flag is the **only** way to enable HF uploads.

The pipeline writes metadata files (`awq_metadata.json` or `build_metadata.json`) and `README.md` into each quantized folder for transparency and reproducibility.

## Test Clients

All CLI harnesses run against the same WebSocket stack; use them to validate behavior end to end. Unless otherwise noted, activate `.venv` (or the lightweight `.venv-local`) before running the commands below.

> **Prompt modes:** every client accepts `--prompt-mode {both,chat,tool}` (or `PROMPT_MODE` env).  
> `both` (default) sends the chat persona prompt.  
> `chat` forces chat-only (identical to `both`).  
> `tool` disables chat prompts entirely (for classifier-only tool deployments).  
> Use this flag whenever the server is deployed in chat-only or tool-only mode so tests match the live configuration. `scripts/warmup.sh` auto-detects `DEPLOY_MODELS` / `DEPLOY_CHAT` / `DEPLOY_TOOL` and forwards the correct choice to `tests/warmup.py` and `tests/bench.py`.

### Warmup Test Client

```bash
source .venv/bin/activate
python3 tests/warmup.py
python3 tests/warmup.py "who was Columbus?"
python3 tests/warmup.py --gender male --personality flirty "hello there"
```

Append `--prompt-mode chat` or `--prompt-mode tool` to mirror single-engine deployments (default `both`).

Environment overrides honored by the client:
- `SERVER_WS_URL` (default `ws://127.0.0.1:8000/ws`)
- `GENDER` (aliases `woman|man`)
- `PERSONALITY` (alias `PERSONA_STYLE`, default `wholesome`)
- `RECV_TIMEOUT_SEC` (default `60`)

Example:

```bash
SERVER_WS_URL=ws://127.0.0.1:8000/ws \
RECV_TIMEOUT_SEC=120 \
python3 tests/warmup.py --gender female --personality savage "hey there"
```

To compare cold vs warm responses on the exact same connection, append `--double-ttfb`. The client will send two identical `start` messages back-to-back, tagging every log/metric with `phase=first|second` so you can spot caching effects without launching separate runs.

### Interactive Live Client

```bash
source .venv/bin/activate
TEXT_API_KEY=your_api_key python3 tests/live.py \
  --server ws://127.0.0.1:8000 \
  --persona default_live_persona
```

Flags:
- `--server`: explicit URL (falls back to `SERVER_WS_URL`, appends `/ws` if missing)
- `--api-key`: override `TEXT_API_KEY`
- `--persona/-p`: persona key from `tests/prompts/live.py` (defaults to `anna_flirty`)
- `--recv-timeout`: override `DEFAULT_RECV_TIMEOUT_SEC`
- `--prompt-mode`: disable chat prompts altogether (`tool`) or keep them (`chat`/`both`) mid-session; persona switches are disabled automatically when chat prompts are off
- positional text: optional opener message

### Personality Switch Test

```bash
source .venv/bin/activate
TEXT_API_KEY=your_api_key python3 tests/personality.py \
  --server ws://127.0.0.1:8000 \
  --switches 3 \
  --delay 2
```

This client requires chat prompts, so invoke it with `--prompt-mode chat` or `both`.

`PERSONA_VARIANTS`, reply lists, and switch counts live in `tests/config`.

### Conversation History Test

```bash
source .venv/bin/activate
TEXT_API_KEY=your_api_key python3 tests/conversation.py --server ws://127.0.0.1:8000
```

Supports `--prompt-mode` for chat-only or tool-only deployments.

Streams a fixed 10-turn script (`tests/messages/conversation.py`) to verify bounded-history eviction and KV-cache reuse.

### Screen Analysis / Toolcall Test

```bash
TEXT_API_KEY=your_api_key python3 tests/screen_analysis.py
```

Ensures toolcall decisions fire before the follow-up chat stream. Override `SERVER_WS_URL`, `GENDER`, or `PERSONALITY` as needed, and pass `--prompt-mode tool` when the chat engine is disabled.

### Tool Regression Test

```bash
TEXT_API_KEY=your_api_key python3 tests/tool.py \
  --server ws://127.0.0.1:8000/ws \
  --timeout 5 \
  --concurrency 4 \
  --limit 50 \
  --max-steps 20
```

- `--timeout`: wait per tool decision (default 5 s)
- `--concurrency`: parallel cases if the tool engine has capacity
- `--limit`: cap the number of replayed cases for faster smoke runs
- `--prompt-mode`: limit prompts to `chat` or `tool` so the suite matches the deployment mode (default `both`)

### Benchmark Client

```bash
source .venv/bin/activate
python3 tests/bench.py -n 32 -c 8
python3 tests/bench.py --gender female --personality flirty "who was Columbus?"
python3 tests/bench.py --url ws://127.0.0.1:8000/ws -n 100 -c 20 --timeout 180
```

Reports p50/p95 latencies while hammering the WebSocket endpoint with concurrent sessions.

Pass `--double-ttfb` to keep each connection open for two sequential transactions. The report prints separate percentile tables (`[first]`, `[second]`) so you can contrast first-token latency for cold vs warm sessions without running the suite twice.

## Persona and History Behavior

- Chat prompts are rendered using each model's own tokenizer
- **vLLM:** Prefix caching reuses any repeated history/prompts within the process. If you swap a companion's system prompt, history KV stays hot.
- **TensorRT-LLM:** Block reuse provides automatic KV cache management without explicit resets.
- To guarantee a hit before speaking, send a `warm_persona` upfront.

## Known Issues

### TRT-LLM Python Version Mismatch

TensorRT-LLM 1.2.0 (and variations like 1.2.0rc5) documentation claims Python 3.11 support, but **Python 3.11 does not work reliably**. Use **Python 3.10** instead.

**Symptoms with Python 3.11:**
- Cryptic import errors during TRT-LLM initialization
- Segmentation faults during engine build
- Incompatible wheel installations failing silently

### CUDA 13.0 Requirement

TensorRT-LLM 1.2.0rc5+ requires **CUDA 13.0** and **PyTorch 2.9.x**. This project uses CUDA 13.0 with `cu130` PyTorch wheels (2.9.1).

If you see pip dependency resolver warnings about torch versions during installation, ensure you're using:
- `torch==2.9.1+cu130` with `--index-url https://download.pytorch.org/whl/cu130`
- `torchvision==0.24.1+cu130` (matching torch 2.9.1)

The build scripts handle this automatically.

### Base Docker Image Selection

**The base Docker image matters a lot.** Installing OpenMPI packages (`libopenmpi3` / `libopenmpi3t64` and `openmpi-common`) via `scripts/setup/bootstrap.sh` can inadvertently **downgrade CUDA below 13.0** depending on the base image's package repositories and pinned versions.

Since TensorRT-LLM requires CUDA 13.0+, this silent downgrade will break deployment with cryptic errors.

**Recommended base images:**

| Platform | Base Image |
|----------|------------|
| NVIDIA (general) | `nvidia/cuda:13.0.0-cudnn-devel-ubuntu24.04` |
| RunPod | `runpod/base:1.0.3-dev-dj-new-pytorch-cuda1300-ubuntu2404` |

**Symptoms of CUDA downgrade:**
- TensorRT-LLM engine build failures
- Runtime errors about incompatible CUDA versions
- `nvcc --version` showing < 13.0 after bootstrap

**Workarounds:**
1. Use a base image with CUDA 13.0 pre-installed and proper apt pinning
2. Pin MPI package versions explicitly via `MPI_VERSION_PIN` environment variable before running bootstrap
3. Verify CUDA version after bootstrap: `nvcc --version` should show 13.0+

## GPU Memory Fractions

GPU memory is allocated based on deployment mode:

- Single model: 90% GPU memory (chat-only or tool-only)
- Both models: Chat gets 70%, Tool gets 20%

Override as needed:

```bash
export CHAT_GPU_FRAC=0.60
export TOOL_GPU_FRAC=0.25
bash scripts/stop.sh && bash scripts/main.sh --trt 4bit <chat_model> <tool_model>
```

**TensorRT-LLM specific:**
- `TRT_KV_FREE_GPU_FRAC` controls KV cache memory (defaults to `CHAT_GPU_FRAC`)
- Engine build uses `TRT_MAX_BATCH_SIZE` to pre-allocate KV cache slots (see [TensorRT-LLM Configuration](#tensorrt-llm-configuration) for details)
