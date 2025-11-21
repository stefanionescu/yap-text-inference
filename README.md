# Yap Text Inference Server

A text inference server optimized for low TTFT and steady text streaming. It can run:
- vLLM chat engine with chat models ranging from 3B–24B
- Engine for tool-call detection
- Both engines together by default; chat-only/tool-only are supported in host scripts and Docker (mixed image)
- FastAPI + WebSocket streaming

## Contents

- [Key Features](#key-features)
- [WebSocket Protocol Highlights](#websocket-protocol-highlights)
- [Quickstart](#quickstart)
- [Linting](#linting)
- [Docker Deployment](#docker-deployment)
- [Quantization Modes (AWQ)](#quantization-modes-awq)
  - [Option 1: Local Quantization (Quantizes on First Run)](#option-1-local-quantization-quantizes-on-first-run)
  - [Option 2: Pre-Quantized AWQ Models (Hugging Face)](#option-2-pre-quantized-awq-models-hugging-face)
- [Local Test Dependencies](#local-test-dependencies)
- [Warmup Test Client](#warmup-test-client)
  - [Basic Usage](#basic-usage)
  - [With a Custom Message](#with-a-custom-message)
  - [With Gender/Style Flags](#with-genderstyle-flags)
  - [Testing Concurrent vs. Sequential Modes](#testing-concurrent-vs-sequential-modes)
  - [Environment Overrides](#environment-overrides)
  - [What It Prints](#what-it-prints)
- [Benchmark Client](#benchmark-client)
- [Viewing Logs](#viewing-logs)
- [Stopping and Restarting](#stopping-and-restarting)
  - [Stop Script Behavior (Deep Clean)](#stop-script-behavior-deep-clean)
- [Health Check](#health-check)
- [Server Status and Capacity](#server-status-and-capacity)
- [Advanced Usage and Tips](#advanced-usage-and-tips)

## Key Features
- Tool-call-first detection. Toolcall signal is sent when detected, then (when chat is deployed) chat tokens always stream regardless.
- Persona/history segmented prompts with prefix caching for KV reuse.
- FP8/INT8 KV cache in vLLM to reduce VRAM and speed up decoding.
- Built-in logit bias that permanently suppresses banned phrases/emoticons (e.g., `*winks*`, `Oh honey`, `:)`). You can override via `CHAT_LOGIT_BIAS_FILE` if needed.
- Interrupts/barge-in via cancel or a new start, plus explicit heartbeats and idle enforcement (150 s default).
- Concurrent connection limiting via a global semaphore (capacity is explicitly configured through the `MAX_CONCURRENT_CONNECTIONS` environment variable so you can match your hardware profile)
- API key authentication for secure access (required, must be set via TEXT_API_KEY environment variable)

## WebSocket Protocol Highlights

- **Start**: `{"type":"start", ...}` begins/queues a turn. Sending another `start` automatically cancels the previous turn for that session (barge-in).
- **Sampling overrides (optional)**: Include a `sampling` object inside the `start` payload to override chat decoding knobs per session, for example:
  `{"type":"start", "...": "...", "sampling":{"temperature":0.8,"top_p":0.85}}`. Supported keys are `temperature` (0.2–1.2), `top_p` (0.6–1.0), `top_k` (10–60), `min_p` (0.0–0.20), `repeat_penalty` (1.0–1.3), `presence_penalty` (0–0.15), and `frequency_penalty` (0–0.15). Any omitted key falls back to the server defaults in `src/config/sampling.py`.
- **Cancel**: `{"type":"cancel"}` (or the literal sentinel `__CANCEL__`) immediately stops both chat and tool engines. The server replies with `{"type":"done","cancelled":true}` (echoing `request_id` when provided).
- **Client end**: `{"type":"end"}` (or the sentinel `__END__`) requests a clean shutdown. The server responds with `{"type":"connection_closed","reason":"client_request"}` before closing with code `1000`.
- **Heartbeat**: `{"type":"ping"}` keeps the socket active during long pauses. The server answers with `{"type":"pong"}`; receiving `{"type":"pong"}` from clients is treated as a no-op. Every ping/ack resets the idle timer.
- **Idle timeout**: Connections with no activity for 150 s (configurable via `WS_IDLE_TIMEOUT_S`) are closed with code `4000`. Send periodic pings or requests to stay connected longer.
- **Sentinel shortcuts**: The default `WS_END_SENTINEL="__END__"` / `WS_CANCEL_SENTINEL="__CANCEL__"` are accepted as raw text frames for clients that can’t emit JSON.
- **Rate limits**: Rolling-window quotas for both general messages and cancel messages are enforced per connection, while persona updates are limited per session. Tune the behavior via `WS_MAX_MESSAGES_PER_WINDOW` / `WS_MESSAGE_WINDOW_SECONDS`, `WS_MAX_CANCELS_PER_WINDOW` / `WS_CANCEL_WINDOW_SECONDS`, and `CHAT_PROMPT_UPDATE_MAX_PER_WINDOW` / `CHAT_PROMPT_UPDATE_WINDOW_SECONDS` (see `src/config/limits.py` for defaults).
- **Capacity guard**: Admissions are gated by a global semaphore (configurable via `MAX_CONCURRENT_CONNECTIONS` and `WS_HANDSHAKE_ACQUIRE_TIMEOUT_S`). When the server returns `server_at_capacity`, retry with backoff.
- **Done frame contract**: Every turn ends with `{"type":"done","usage":{...}}` when it succeeds, or `{"type":"done","cancelled":true}` when it’s interrupted (explicit cancel or barge-in).

## Quickstart

### Required Environment Variables

Set the compulsory environment variables before invoking any host script:

```bash
export TEXT_API_KEY="my_super_secret_key_2024"    # Required for every API call
export HF_TOKEN="hf_your_api_token"               # Required even for private/gated HF repos
export MAX_CONCURRENT_CONNECTIONS=32              # Required capacity guard (pick a value for your GPU)
```

`HUGGINGFACE_HUB_TOKEN` is also accepted and will be mirrored into `HF_TOKEN` automatically.

1) Install deps and start the server

```bash
# Both models (default) - always runs in background with auto-tail
bash scripts/main.sh [awq] <chat_model> <tool_model> [deploy_mode]

# Single-model forms (host scripts only; Docker always runs both)
bash scripts/main.sh [awq] chat <chat_model>
bash scripts/main.sh [awq] tool <tool_model>

# Behavior: Auto-detached deployment + log tailing
# Ctrl+C stops tail only, deployment continues
# Use scripts/stop.sh to stop deployment
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
```

This will:
- Check GPU availability
- Install Python deps from `requirements.txt`
- Export environment defaults
- Launch `uvicorn src.server:app --port 8000`
- Always runs in background with auto-detached process isolation
- Auto-tails logs (Ctrl+C stops tail only)

## Linting

Create/activate a virtualenv, install runtime + dev deps, then run the integrated lint script:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
bash scripts/lint.sh
```

`scripts/lint.sh` runs Ruff across `src` and `test`, then ShellCheck over every tracked `*.sh`, exiting non-zero if anything fails.

## Docker Deployment

You can deploy the server in Docker using the stacks in `docker/awq` (pre-quantized AWQ) and `docker/mixed` (embed-only: pre-quantized AWQ and/or float, supports chat/tool/both and mixed quant):

```bash
# AWQ (pre-quantized models)
DOCKER_USERNAME=youruser docker/awq/build.sh
docker run -d --gpus all --name yap-awq \
  -e AWQ_CHAT_MODEL=yapwithai/impish-12b-awq \
  -e AWQ_TOOL_MODEL=yapwithai/hammer-2.1-3b-awq \
  -e TEXT_API_KEY=your_secret_key \
  -e HF_TOKEN=hf_your_api_token \
  -e MAX_CONCURRENT_CONNECTIONS=32 \
  -p 8000:8000 youruser/yap-text-inference-awq:latest

# Base (float/GPTQ, pre-quantized AWQ, or runtime AWQ)
DOCKER_USERNAME=youruser DEPLOY_MODELS=both CHAT_MODEL=org/chat TOOL_MODEL=org/tool docker/mixed/build.sh  # builds :both-fp8
docker run -d --gpus all --name yap-mixed \
  -e TEXT_API_KEY=your_secret_key \
  -e HF_TOKEN=hf_your_api_token \
  -e MAX_CONCURRENT_CONNECTIONS=32 \
  -p 8000:8000 youruser/yap-text-inference-mixed:both-fp8
```

See `docker/awq/README.md` and `docker/mixed/README.md` for build arguments, image behavior, and run options.

## Quantization Modes (AWQ)

4-bit mode (AWQ via vLLM auto-AWQ).

### Option 1: Local Quantization (Quantizes on First Run)

```bash
# Uses float (non-GPTQ) chat model weights and quantizes BOTH chat and tool models at load
bash scripts/main.sh awq SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b

# With concurrent mode
CONCURRENT_MODEL_CALL=1 bash scripts/main.sh awq SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b
```

### Option 2: Pre-Quantized AWQ Models (Hugging Face)

```bash
# Use pre-quantized AWQ models (no quantization step, faster startup)
AWQ_CHAT_MODEL=yapwithai/impish-12b-awq AWQ_TOOL_MODEL=yapwithai/hammer-2.1-3b-awq bash scripts/main.sh awq

# Chat-only with pre-quantized model
AWQ_CHAT_MODEL=yapwithai/impish-12b-awq bash scripts/main.sh awq chat

# Tool-only with pre-quantized model  
AWQ_TOOL_MODEL=yapwithai/hammer-2.1-3b-awq bash scripts/main.sh awq tool

# With concurrent mode
AWQ_CHAT_MODEL=yapwithai/impish-12b-awq AWQ_TOOL_MODEL=yapwithai/hammer-2.1-3b-awq CONCURRENT_MODEL_CALL=1 bash scripts/main.sh awq

# Use your own pre-quantized AWQ models (auto-detected)
AWQ_CHAT_MODEL=your-org/chat-awq AWQ_TOOL_MODEL=your-org/tool-awq bash scripts/main.sh awq
```

## Local Test Dependencies

If you just want to run the WebSocket test clients (warmup, live, conversation, etc.) on a laptop or CPU-only machine, don’t install the GPU-heavy `requirements.txt`. Instead:

```bash
python3 -m venv .venv-local
source .venv-local/bin/activate
pip install -r requirements-local.txt
```

This installs the lightweight client deps (`websockets`, `httpx`, `orjson`) without pulling CUDA wheels, so macOS users can run `python3 test/live.py ...` without errors. Use the full `requirements.txt` only when you need to run the actual inference server.

## Warmup Test Client

Activate the virtualenv created by the setup scripts:

```bash
source .venv/bin/activate
```

### Basic Usage

```bash
python3 test/warmup.py
```

### With a Custom Message

```bash
python3 test/warmup.py "who was Columbus?"
```

### With Gender/Style Flags

```bash
python3 test/warmup.py --gender male --style flirty "hello there"
```

### Testing Concurrent vs. Sequential Modes

```bash
# Test sequential mode (default)
python3 test/warmup.py "write a simple hello world function"

# Test concurrent mode
# Terminal 1: Start server with concurrent mode (auto → FP8)
NUKE_ALL=1 bash scripts/stop.sh  # Stop previous deployment
CONCURRENT_MODEL_CALL=1 bash scripts/main.sh SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b

# Terminal 2: Test the same query (after server is ready)
python3 test/warmup.py "write a simple hello world function"

# Test the roleplay-optimized model
# Terminal 1: Start server with Wingless_Imp_8B (auto → FP8)
NUKE_ALL=1 bash scripts/stop.sh  # Stop previous deployment
bash scripts/main.sh SicariusSicariiStuff/Wingless_Imp_8B MadeAgents/Hammer2.1-1.5b

# Terminal 2: Test creative/roleplay query (after server is ready)
python3 test/warmup.py "*waves hand* Tell me a creative story about a lonely dragon"
```

The concurrent mode should show lower `ttfb_ms` for chat responses where the toolcall model returns false.

### Environment Overrides

- `SERVER_WS_URL` (default `ws://127.0.0.1:8000/ws`)
- `GENDER` (default `female`) — aliases accepted: `woman|man`
- `PERSONA_STYLE` (default `wholesome`)
- `RECV_TIMEOUT_SEC` (default `60`)

Examples:

```bash
SERVER_WS_URL=ws://127.0.0.1:8000/ws python3 test/warmup.py
RECV_TIMEOUT_SEC=120 python3 test/warmup.py --gender female --style savage "hey there"
```

### What It Prints

- An ACK line confirming session time and effective `gender`/`persona_style`.
- Two JSON lines when streaming completes:
  - Metrics: `{ "type": "metrics", "ttfb_ms": ..., "total_ms": ..., "stream_ms": ..., "chunks": ..., "chars": ... }`
  - Final text: `{ "type": "final_text", "text": "..." }`

All WebSocket helper clients automatically append `/ws` (when it’s missing) and the API key query parameter to whatever origin you provide.

All of the CLI test clients share the same sampling override flags: `--temperature`, `--top-p`, `--top-k`, and `--repeat-penalty`. Each flag maps directly to the server’s chat defaults (temperature=`1.0`, top-p=`0.80`, top-k=`40`, repeat-penalty=`1.05`). Omit them to stick with the server configuration; specify any subset to experiment with decoding behavior on a per-run basis.

### Interactive Live Client

Streams a real-time conversation you can steer from the CLI, hot-reloading persona definitions from `test/prompts/live.py`. If you omit `--server`, the client falls back to `SERVER_WS_URL` (default `ws://127.0.0.1:8000/ws`). When you do provide `--server`, you can point at either the full `/ws` endpoint or just the origin (`ws://host:port`); the client automatically appends `/ws` and your API key.

```bash
TEXT_API_KEY=your_api_key python3 test/live.py \
  --server ws://127.0.0.1:8000 \
  --persona default_live_persona
```

Flags:

- `--server`: target WebSocket URL (defaults to `SERVER_WS_URL`; accepts origins without `/ws`)
- `--api-key`: override `TEXT_API_KEY` env for the session
- `--persona/-p`: persona key from `test/prompts/live.py` (defaults to `anna_flirty`)
- `--recv-timeout`: receive timeout in seconds (default `DEFAULT_RECV_TIMEOUT_SEC`)
- positional arguments: optional opener message; falls back to warmup defaults otherwise

### Personality Switch Test

Exercises persona updates, ensuring chat prompt swaps and history stitching behave correctly.

```bash
TEXT_API_KEY=your_api_key python3 test/personality.py \
  --server ws://127.0.0.1:8000 \
  --switches 3 \
  --delay 2
```

`PERSONA_VARIANTS`, reply lists, and switch counts live in `test/config`.

### Conversation History Test

Streams a fixed 10-turn conversation (same persona throughout) to verify bounded-history eviction and KV-cache reuse while logging TTFB/first-word metrics for every exchange.

```bash
TEXT_API_KEY=your_api_key python3 test/conversation.py --server ws://127.0.0.1:8000
```

Prompts are sourced from `CONVERSATION_HISTORY_PROMPTS` in `test/config/messages.py`.

### Screen Analysis / Toolcall Test

Runs the end-to-end toolcall → follow-up flow used for screen analysis, asserting the first turn triggers `toolcall == YES` and that the follow-up response streams successfully.

```bash
TEXT_API_KEY=your_api_key python3 test/screen_analysis.py
```

Override defaults via `SERVER_WS_URL`, `GENDER`, or `PERSONALITY` environment variables when needed.

## Benchmark Client

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

## Viewing Logs

All deployment and server logs are unified in a single `server.log` file.

```bash
# All logs (deployment + server activity)
tail -f server.log
```

Note: `scripts/main.sh` auto-tails all logs by default. Ctrl+C detaches from tail without stopping the deployment.

## Stopping and Restarting

After initial deployment, you can use these commands to stop and/or restart the server:

```bash
# Light stop (preserve AWQ models and dependencies)
NUKE_ALL=0 bash scripts/stop.sh

# Quick restart using existing AWQ models
bash scripts/restart.sh [both|chat|tool]

# Restart and reinstall dependencies (e.g., refresh venv)
bash scripts/restart.sh both --install-deps

# Full stop and restart cycle
bash scripts/stop.sh && bash scripts/main.sh awq <chat_model> <tool_model>
```

### Stop Script Behavior (Deep Clean)

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

## Health Check

```bash
curl -s http://127.0.0.1:8000/healthz
```

## Server Status and Capacity

```bash
# With API key (required)
curl -H "X-API-Key: your_api_key" http://127.0.0.1:8000/status

# Via query parameter
curl "http://127.0.0.1:8000/status?api_key=your_api_key"
```

Returns server status and connection capacity information, including current active connections and limits.

## Advanced Usage and Tips

Looking for logs, status/health endpoints, security configuration, restart flows, environment variables, WebSocket protocol details, or pushing AWQ exports? See `ADVANCED.md`.