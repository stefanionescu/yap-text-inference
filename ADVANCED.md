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
| `VLLM_ATTENTION_BACKEND` | auto | Force attention backend (e.g., `FLASH_ATTN`, `FLASHINFER`) |
| `ENFORCE_EAGER` | `0` | Disable CUDA graphs for debugging |
| `VLLM_ALLOW_LONG_MAX_MODEL_LEN` | `1` | Allow context lengths beyond model config |
| `KV_DTYPE` | auto | KV cache dtype (`auto`, `fp8`, `int8`) |
| `AWQ_CACHE_DIR` | `.awq` | Local cache for AWQ exports |

**Cache Management:**
- vLLM resets prefix caches periodically to prevent fragmentation
- Configure interval with `CACHE_RESET_INTERVAL_SECONDS` (default: 600)

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

TRT-LLM engines have `max_batch_size` baked in at build time. This is not the same as `MAX_CONCURRENT_CONNECTIONS`.

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

The server validates that `TRT_BATCH_SIZE` ≤ engine's max at startup.

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

`scripts/lint.sh` runs Ruff on Python and ShellCheck on shell scripts.

## API — WebSocket `/ws`

The server uses persistent WebSocket connections. Each client provides a `session_id`, and a connection can handle multiple requests with automatic interruption support.

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
- **Connection limit**: New connections are limited by `MAX_CONCURRENT_CONNECTIONS`. When the server returns `server_at_capacity`, retry with backoff.
- **Done frame**: Every turn ends with `{"type":"done","usage":{...}}` on success, or `{"type":"done","cancelled":true}` when interrupted.

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

Start a turn

```json
{
  "type": "start",
  "session_id": "<stable-per-user uuid>",
  "persona_text": "...optional full persona...",
  "persona_style": "savage|flirty|...",
  "gender": "woman|man",
  "user_identity": "woman|man|non-binary",
  "history": [
    {"role": "user", "content": "previous message"},
    {"role": "assistant", "content": "previous reply"}
  ],
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

- Server replies with `{"type":"pong"}` and resets the idle timer (default idle timeout: 150s, set via `WS_IDLE_TIMEOUT_S`).
- Incoming `{"type":"pong"}` frames are treated as no-ops so clients can mirror the heartbeat without extra logic.

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
  "message": "Server cannot accept new connections. Please try again later."
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

- **Per connection:** Messages and cancels have rate limits. Configure via `WS_MAX_MESSAGES_PER_WINDOW` / `WS_MESSAGE_WINDOW_SECONDS` and `WS_MAX_CANCELS_PER_WINDOW` / `WS_CANCEL_WINDOW_SECONDS`.
- **Per session:** Persona updates have their own limit via `CHAT_PROMPT_UPDATE_MAX_PER_WINDOW` / `CHAT_PROMPT_UPDATE_WINDOW_SECONDS`.

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

**Required whenever `--push-quant` is present:**
- `HF_TOKEN` (or `HUGGINGFACE_HUB_TOKEN`) with write access
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

All test clients run against the WebSocket endpoint. Run them via `scripts/activate.sh` (e.g., `bash scripts/activate.sh python3 tests/warmup.py`) or source `.venv-local/bin/activate` for CPU-only testing.

> **Tool-only deployments:** Pass `--no-chat-prompt` to skip chat prompts. `scripts/warmup.sh` auto-detects the deploy mode and forwards this flag when needed.

### Warmup Test Client

```bash
# run these after entering the venv via 'bash scripts/activate.sh'
python3 tests/warmup.py
python3 tests/warmup.py "who was Columbus?"
python3 tests/warmup.py --gender male --personality flirty "hello there"
```

Append `--no-chat-prompt` for tool-only deployments where no chat model is available.

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

Append `--double-ttfb` to send two identical requests back-to-back and compare cold vs warm latency.

### Interactive Live Client

```bash
# run inside the scripts/activate.sh environment
TEXT_API_KEY=your_api_key python3 tests/live.py \
  --server ws://127.0.0.1:8000 \
  --persona default_live_persona
```

Flags:
- `--server`: explicit URL (falls back to `SERVER_WS_URL`, appends `/ws` if missing)
- `--api-key`: override `TEXT_API_KEY`
- `--persona/-p`: persona key from `tests/prompts/detailed.py` (defaults to `anna_flirty`)
- `--recv-timeout`: override `DEFAULT_RECV_TIMEOUT_SEC`
- `--no-chat-prompt`: disable chat prompts for tool-only deployments; persona switches are disabled automatically when chat prompts are off
- positional text: optional opener message

### Personality Switch Test

```bash
# run inside the scripts/activate.sh environment
TEXT_API_KEY=your_api_key python3 tests/personality.py \
  --server ws://127.0.0.1:8000 \
  --switches 3 \
  --delay 2
```

Cycles through 5 personalities while alternating genders and maintaining conversation history. Requires a chat model.

`PERSONA_VARIANTS`, reply lists, and switch counts live in `tests/config`.

### Gender Switch Test

```bash
# run inside the scripts/activate.sh environment
TEXT_API_KEY=your_api_key python3 tests/gender.py \
  --server ws://127.0.0.1:8000 \
  --switches 3 \
  --delay 2
```

Cycles through gender configurations while maintaining conversation history. Requires a chat model.

Both tests share the same CLI flags:
- `--switches`: Number of chat prompt switches (default 5)
- `--delay`: Seconds between switches (default 2)
- Sampling overrides: `--temperature`, `--top_p`, `--top_k`, `--min_p`, `--repetition_penalty`

### Conversation History Test

```bash
# run inside the scripts/activate.sh environment
TEXT_API_KEY=your_api_key python3 tests/conversation.py --server ws://127.0.0.1:8000
```

Supports `--no-chat-prompt` for tool-only deployments.

Streams a 10-turn script to test history eviction and KV-cache reuse.

### Screen Analysis / Toolcall Test

```bash
TEXT_API_KEY=your_api_key python3 tests/screen_analysis.py
```

Tests that toolcall decisions fire before chat streaming. Pass `--no-chat-prompt` for tool-only deployments.

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
- `--no-chat-prompt`: skip chat prompts for tool-only deployments

### Benchmark Client

```bash
# run inside the scripts/activate.sh environment
python3 tests/bench.py -n 32 -c 8
python3 tests/bench.py --gender female --personality flirty "who was Columbus?"
python3 tests/bench.py --url ws://127.0.0.1:8000/ws -n 100 -c 20 --timeout 180
```

Reports p50/p95 latencies under concurrent load.

Pass `--double-ttfb` to run two sequential transactions per connection and compare cold vs warm latency.

## Persona and History Behavior

- Chat prompts are rendered using each model's tokenizer
- **vLLM:** Prefix caching reuses repeated prompts automatically. Swapping the system prompt keeps history KV hot.
- **TensorRT-LLM:** Block reuse handles KV cache automatically.

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
