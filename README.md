# Yap Text Inference Server

A vLLM text inference server optimized for low TTFT. It can run:
- Chat engine for roleplay
- Engine for tool-call detection
- Both engines together by default; chat-only/tool-only are supported in host scripts and Docker (mixed image)
- FastAPI + WebSocket streaming

## Contents

- [Key Features](#key-features)
- [Quickstart](#quickstart)
- [Docker Deployment](#docker-deployment)
- [Quantization](#quantization)
  - [Option 1: Local Quantization (Quantizes on First Run)](#option-1-local-quantization-quantizes-on-first-run)
  - [Option 2: Pre-Quantized Models](#option-2-pre-quantized-models)
- [Local Test Dependencies](#local-test-dependencies)
- [Warmup Test Client](#warmup-test-client)
  - [Basic Usage](#basic-usage)
  - [With a Custom Message](#with-a-custom-message)
  - [With Gender/Style Flags](#with-genderstyle-flags)
  - [Testing Concurrent vs. Sequential Modes](#testing-concurrent-vs-sequential-modes)
  - [Environment Overrides](#environment-overrides)
- [Interactive Live Client](#interactive-live-client)
- [Personality Switch Test](#personality-switch-test)
- [Conversation History Test](#conversation-history-test)
- [Screen Analysis / Toolcall Test](#screen-analysis--toolcall-test)
- [Benchmark Client](#benchmark-client)
- [Stopping and Restarting](#stopping-and-restarting)
  - [Stop Script Behavior (Deep Clean)](#stop-script-behavior-deep-clean)
- [Health Check](#health-check)
- [Advanced Usage and Tips](#advanced-usage-and-tips)

## Key Features
- Tool-call-first detection. Toolcall signal is sent when detected, then (when chat is deployed) chat tokens always stream regardless.
- Persona/history segmented prompts with prefix caching for KV reuse.
- FP8/INT8 KV cache in vLLM to reduce VRAM and speed up decoding.
- Built-in logit bias that permanently suppresses banned phrases/emoticons (e.g., `*winks*`, `Oh honey`, `:)`). You can override via `CHAT_LOGIT_BIAS_FILE` if needed.
- Interrupts/barge-in via cancel or a new start, plus explicit heartbeats and idle enforcement (150 s default).
- Concurrent connection limiting via a global semaphore (capacity is explicitly configured through the `MAX_CONCURRENT_CONNECTIONS` environment variable so you can match your hardware profile)
- API key authentication for secure access (required, must be set via TEXT_API_KEY environment variable)

## Quickstart

### Required Environment Variables

Set the compulsory environment variables before invoking any host script:

```bash
export TEXT_API_KEY="my_super_secret_key_2024"    # Required for every API call
export HF_TOKEN="hf_your_api_token"               # Required even for private/gated HF repos
export MAX_CONCURRENT_CONNECTIONS=20              # Required capacity guard (pick a value for your GPU)
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

## Docker Deployment

You can deploy the server in Docker using the stacks in `docker/awq` (pre-quantized AWQ) and `docker/mixed` (embed-only: pre-quantized AWQ and/or float, supports chat/tool/both and mixed quant):

```bash
# AWQ (pre-quantized models)
DOCKER_USERNAME=youruser docker/awq/build.sh
docker run -d --gpus all --name yap-awq \
  -e CHAT_MODEL=yapwithai/impish-12b-awq \
  -e TOOL_MODEL=yapwithai/hammer-2.1-3b-awq \
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

## Quantization

4-bit mode AWQ/W4A16 via llmcompressor + vLLM (with AutoAWQ fallback for Qwen & Mistral 3).

### Option 1: Local Quantization (Quantizes on First Run)

```bash
# Uses float (non-GPTQ) chat model weights and quantizes BOTH chat and tool models at load
bash scripts/main.sh awq SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b

# With concurrent mode
CONCURRENT_MODEL_CALL=1 bash scripts/main.sh awq SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b
```

Local quantization runs [`llmcompressor`](https://github.com/vllm-project/llm-compressor) `oneshot()` with the AWQ modifier (pinned at version 0.8.1). Override `AWQ_CALIB_DATASET`, `AWQ_NSAMPLES`, or `AWQ_SEQLEN` to tune the calibration recipe (default dataset: `open_platypus`, with automatic fallback from `pileval` on older llmcompressor builds).  
> **AutoAWQ fallback:** Qwen2/Qwen3 and Mistral 3 checkpoints automatically switch to [AutoAWQ 0.2.9](https://github.com/AutoAWQ/AutoAWQ) because llmcompressor cannot yet trace their hybrid forward graphs. Other architectures continue to use llmcompressor.  
> To coexist with `vllm==0.11.2`/`torch==2.9.0`, the setup scripts install `llmcompressor` with `--no-deps`. If you manage the environment manually, mirror this behavior (`pip install llmcompressor==0.8.1 --no-deps`) after installing the base requirements.

### Option 2: Pre-Quantized Models

The server now auto-detects **any** pre-quantized repo whose name includes common markers:
- `awq` or explicit W4A16 hints (`w4a16`, `nvfp4`, `compressed-tensors`, `autoround`)
- `gptq` (including `gptq_marlin` exports)

If the repo path advertises one of these markers, Yap skips runtime quantization and runs it directly—even if the model isn’t on the default allowlist. This matches the config enforcement logic described in `src/config/models.py`.

```bash
# Pre-quantized AWQ (chat + tool)
bash scripts/main.sh \
  yapwithai/impish-12b-awq \
  yapwithai/hammer-2.1-3b-awq

# Chat-only AWQ
bash scripts/main.sh chat yapwithai/impish-12b-awq

# Tool-only AWQ
bash scripts/main.sh tool yapwithai/hammer-2.1-3b-awq

# AWQ with concurrent mode
CONCURRENT_MODEL_CALL=1 \
bash scripts/main.sh \
  yapwithai/impish-12b-awq \
  yapwithai/hammer-2.1-3b-awq

# Custom AWQ or W4A16 (auto-detected compressed tensors)
bash scripts/main.sh \
  leon-se/gemma-3-27b-it-qat-W4A16-G128 \
  your-org/tool-awq

# Pre-quantized GPTQ chat model (tool stays float)
CONCURRENT_MODEL_CALL=1 \
bash scripts/main.sh \
  SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64 \
  MadeAgents/Hammer2.1-3b

# GPTQ-only chat deployment
bash scripts/main.sh chat SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32
```

> **Note on llmcompressor / W4A16 exports:** Whether the model lives locally or on Hugging Face, the code inspects `quantization_config.json` (and `awq_metadata.json` when present) to pick the correct vLLM backend (e.g., `compressed-tensors` for W4A16/NVFP4 checkpoints). Just set `HF_TOKEN`/`HUGGINGFACE_HUB_TOKEN` for private repos and point `CHAT_MODEL` / `TOOL_MODEL` at the repo IDs—no re-quantization step is needed. GPTQ repos are likewise detected automatically and routed through the GPTQ runtime. Qwen-family and Mistral-3 exports are tagged as AutoAWQ in metadata so downstream consumers know which quantizer produced the checkpoint.

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
# Test sequential mode (set CONCURRENT_MODEL_CALL=0)
CONCURRENT_MODEL_CALL=0 python3 test/warmup.py "write a simple hello world function"

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

## Interactive Live Client

Streams a real-time conversation you can steer from the CLI, hot-reloading persona definitions from `test/prompts/live.py`. If you omit `--server`, the client falls back to `SERVER_WS_URL` (default `ws://127.0.0.1:8000/ws`). When you do provide `--server`, you can point at either the full `/ws` endpoint or just the origin (`ws://host:port`); the client automatically appends `/ws` and your API key.

Activate the virtualenv created by the setup scripts:

```bash
source .venv/bin/activate
```

Then run:

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

## Personality Switch Test

Exercises persona updates, ensuring chat prompt swaps and history stitching behave correctly.

Activate the virtualenv created by the setup scripts:

```bash
source .venv/bin/activate
```

Then run:

```bash
TEXT_API_KEY=your_api_key python3 test/personality.py \
  --server ws://127.0.0.1:8000 \
  --switches 3 \
  --delay 2
```

`PERSONA_VARIANTS`, reply lists, and switch counts live in `test/config`.

## Conversation History Test

Streams a fixed 10-turn conversation (same persona throughout) to verify bounded-history eviction and KV-cache reuse while logging TTFB/first-word metrics for every exchange.

Activate the virtualenv created by the setup scripts:

```bash
source .venv/bin/activate
```

Then run:

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

Activate the virtualenv created by the setup scripts:

```bash
source .venv/bin/activate
```

Then, run concurrent sessions and report p50/p95 latencies:

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

## Stopping and Restarting

After initial deployment, you can use these commands to stop and/or restart the server:

```bash
# Light stop (preserve AWQ models and dependencies)
NUKE_ALL=0 bash scripts/stop.sh

# Quick restart using existing AWQ models
bash scripts/restart.sh [both|chat|tool]

# Restart and reinstall dependencies (e.g., refresh venv)
bash scripts/restart.sh both --install-deps

# Reset models/quantization without reinstalling deps
bash scripts/restart.sh --reset-models --deploy-mode both \
  --chat-model SicariusSicariiStuff/Impish_Nemo_12B \
  --tool-model MadeAgents/Hammer2.1-3b \
  --chat-quant fp8 \
  --tool-quant awq

# Auto-detect pre-quantized repos (AWQ/GPTQ) during reset
bash scripts/restart.sh --reset-models --deploy-mode chat \
  --chat-model dreamgen/opus-v1-34b-awq
bash scripts/restart.sh --reset-models --deploy-mode chat \
  --chat-model SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64

# Full stop and restart cycle
bash scripts/stop.sh && bash scripts/main.sh awq <chat_model> <tool_model>
```

Caches are wiped by default during model resets; they are only preserved automatically when the requested models *and* quantization match the previous deployment.

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

## Advanced Usage and Tips

Looking for logs, status/health endpoints, security configuration, restart flows, environment variables, WebSocket protocol details, or pushing AWQ exports? See `ADVANCED.md`.