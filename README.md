# Yap Text Inference Server

A vLLM text inference server optimized for dual model deployment. It can run:
- Chat engine for roleplay
- Engine for tool-call detection
- Both engines together by default; chat-only/tool-only are supported in host scripts and Docker (mixed image)
- FastAPI + WebSocket streaming

## Contents

- [Key Features](#key-features)
- [Quickstart](#quickstart)
- [Docker Deployment](#docker-deployment)
- [Quantization](#quantization)
  - [Option 1: Local Quantization](#option-1-local-quantization)
  - [Option 2: Pre-Quantized Models](#option-2-pre-quantized-models)
- [Local Test Dependencies](#local-test-dependencies)
- [Test Clients](#test-clients)
- [Stopping and Restarting](#stopping-and-restarting)
  - [Stop Script Behavior](#stop-script-behavior)
- [Health Check](#health-check)
- [Advanced Usage and Tips](#advanced-usage-and-tips)

## Key Features
- Dual-engine architecture (chat + tool) with optional chat-only/tool-only modes and concurrent streaming to keep both models busy.
- Tool-call-first detection: tool decisions fire before chat tokens, while chat still streams for every turn so UX never stalls.
- Persona/history segmented prompts with prefix caching and FP8/INT8 KV reuse to keep latency low across restarts.
- Integrated quantization pipeline (FP8 default, AWQ/GPTQ/W4A16 auto-detect, AutoAWQ fallbacks) plus configurable logit bias for banned phrases.
- Built-in resiliency: interrupts/barge-in, heartbeats, idle watchdog (150 s default), and sliding-window rate limits on both messages and cancels.
- Secure multi-tenant guardrails via required API keys and a global semaphore driven by `MAX_CONCURRENT_CONNECTIONS`.

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

### Option 1: Local Quantization

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

This installs the lightweight client deps (`websockets`, `httpx`, `orjson`) without pulling CUDA wheels, so macOS users can run `python3 tests/live.py ...` without errors. Use the full `requirements.txt` only when you need to run the actual inference server.

## Test Clients

Need to smoke-test the stack without touching production traffic? Every CLI harness now has a consolidated home in [`ADVANCED.md#test-clients`](ADVANCED.md#test-clients). Highlights:

- [`tests/warmup.py`](ADVANCED.md#warmup-test-client) – one-turn toolcall + chat smoke. Supports `--gender`, `--personality` (alias: `--style`) and honors `SERVER_WS_URL`, `PERSONALITY`, `GENDER`, and `RECV_TIMEOUT_SEC` env vars. Set `CONCURRENT_MODEL_CALL=0` only if you explicitly want to compare sequential mode to the default concurrent pipeline.
- [`tests/live.py`](ADVANCED.md#interactive-live-client) – interactive streaming client that hot-reloads personas from `tests/prompts/live.py`.
- [`tests/personality.py`](ADVANCED.md#personality-switch-test) – exercises persona swaps and history stitching to ensure cache hits are preserved.
- [`tests/conversation.py`](ADVANCED.md#conversation-history-test) – deterministic 10-turn trace for KV eviction and latency metrics.
- [`tests/screen_analysis.py`](ADVANCED.md#screen-analysis--toolcall-test) – validates the toolcall branch used by screen analysis flows.
- [`tests/tool.py`](ADVANCED.md#tool-regression-test) – regression harness for the screenshot/tool-call classifier (timeouts, concurrency, limit flags).
- [`tests/bench.py`](ADVANCED.md#benchmark-client) – load generator that reports p50/p95 latencies for concurrent sessions.

All of them run happily on the lightweight `requirements-local.txt` environment described above; check the advanced guide for full command examples.

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

Key restart knobs:
- `--keep-models` (default) reuses cached AWQ exports; combine with `NUKE_ALL=0` for sub-minute restarts.
- `--reset-models` wipes caches before relaunching different repos or quantization.
- `--install-deps` reinstalls `.venv` before launching.
- `--push-awq` uploads the cached AWQ build; see [`ADVANCED.md#pushing-awq-exports-to-hugging-face`](ADVANCED.md#pushing-awq-exports-to-hugging-face) for required env vars.

Caches are wiped by default during model resets; they are only preserved automatically when the requested models *and* quantization match the previous deployment.

### Stop Script Behavior

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