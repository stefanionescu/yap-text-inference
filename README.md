# Yap Text Inference Server

A vLLM text inference server optimized for pairing a chat model with a lightweight screenshot-intent classifier. Chat generations run on vLLM; the tool router is a direct transformers classifier (no vLLM, no quantization). It can run:
- A vLLM chat engine for roleplay / assistant flows
- A classifier-only tool router (takes screenshots or skips them)
- Either engine independently or both together
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
- Chat + classifier deployment with optional chat-only or classifier-only modes.
- Tool-call-first detection: tool decisions fire before chat tokens, while chat still streams for every turn so UX never stalls.
- Persona/history segmented prompts with prefix caching and FP8/INT8 KV reuse to keep latency low across restarts.
- Integrated quantization pipeline (FP8 default, AWQ/GPTQ/W4A16 auto-detect, AutoAWQ fallbacks) plus configurable logit bias for banned phrases.
- Built-in resiliency: interrupts/barge-in, heartbeats, idle watchdog (150 s default), and sliding-window rate limits on both messages and cancels.
- Secure multi-tenant guardrails via required API keys and a global semaphore driven by `MAX_CONCURRENT_CONNECTIONS`.

## Quickstart

### Required Environment Variables

Set the compulsory environment variables before invoking any host script:

```bash
export TEXT_API_KEY="my_super_secret_key"    # Required for every API call
export HF_TOKEN="hf_your_api_token"          # Required even for private/gated HF repos
export MAX_CONCURRENT_CONNECTIONS=32         # Required capacity guard
```

`HUGGINGFACE_HUB_TOKEN` is also accepted and will be mirrored into `HF_TOKEN` automatically.

1) Install deps and start the server

```bash
# Chat + classifier (default) - auto-detached deployment with log tailing
bash scripts/main.sh [4bit|8bit] <chat_model> <classifier_model>

# Chat-only / classifier-only helpers (host scripts only; Docker always runs both)
bash scripts/main.sh [4bit|8bit] chat <chat_model>
bash scripts/main.sh tool <classifier_model>

# Ctrl+C stops the log tail only; use scripts/stop.sh to stop the server
```

Default GPU allocation:
- Chat deployments reserve 70% of GPU memory when a classifier is also configured (override with `CHAT_GPU_FRAC`).
- The classifier (when it runs on GPU) is capped at 20% by default; override with `TOOL_GPU_FRAC`.
- Chat-only and tool-only mode allocates 90% to the chat engine

Tool routing relies on a PyTorch classifier (default: `yapwithai/yap-longformer-screenshot-intent`). You can swap it via `TOOL_MODEL`, but the model must be compatible with `AutoModelForSequenceClassification`.

Examples:
```bash
# Float chat model (auto → FP8)
bash scripts/main.sh SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent

# Float roleplay model (auto → FP8) with classifier routing
bash scripts/main.sh SicariusSicariiStuff/Wingless_Imp_8B yapwithai/yap-longformer-screenshot-intent

# GPTQ chat model (auto → GPTQ) + classifier
bash scripts/main.sh SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64 yapwithai/yap-longformer-screenshot-intent
```

This will:
- Check GPU availability
- Install Python deps from `requirements.txt`
- Export environment defaults
- Launch `uvicorn src.server:app --port 8000`
- Always runs in background with auto-detached process isolation
- Auto-tails logs (Ctrl+C stops tail only)

## Docker Deployment

Deploy the server in Docker using the AWQ stack in `docker/`:

```bash
# Build the image
DOCKER_USERNAME=youruser DEPLOY_MODELS=both ./docker/build.sh

# Run (chat + classifier)
docker run -d --gpus all --name yap-awq \
  -e DEPLOY_MODELS=both \
  -e TOOL_MODEL=yapwithai/yap-longformer-screenshot-intent \
  -e TEXT_API_KEY=your_secret_key \
  -e HF_TOKEN=hf_your_api_token \
  -e MAX_CONCURRENT_CONNECTIONS=32 \
  -p 8000:8000 youruser/yap-text-inference-awq:both

# Chat-only (uses default model: cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit)
DOCKER_USERNAME=youruser DEPLOY_MODELS=chat ./docker/build.sh
docker run -d --gpus all --name yap-chat \
  -e DEPLOY_MODELS=chat \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 youruser/yap-text-inference-awq:chat

# Classifier-only
DOCKER_USERNAME=youruser DEPLOY_MODELS=tool ./docker/build.sh
docker run -d --gpus all --name yap-tool \
  -e DEPLOY_MODELS=tool \
  -e TOOL_MODEL=yapwithai/yap-longformer-screenshot-intent \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 youruser/yap-text-inference-awq:tool
```

> Tool classifiers are standard PyTorch weights loaded via `AutoModelForSequenceClassification`. They're cached locally (e.g., `$REPO/.run`, `.hf`, or `/app/models/tool` inside Docker) so restarts reuse them instantly.

See `docker/README.md` for build arguments, image behavior, and run options.

## Quantization

4-bit mode AWQ/W4A16 via llmcompressor + vLLM (with AutoAWQ fallback for Qwen & Mistral 3).
Pass `4bit` or `8bit` to the host scripts. The logs will spell out the actual backend that gets selected (`AWQ`, `GPTQ`, `FP8`, `INT8`) so you always know what’s running.

### Option 1: Local Quantization

```bash
# Uses float (non-GPTQ) chat model weights and quantizes the chat engine at load
bash scripts/main.sh 4bit SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent
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
# Pre-quantized AWQ chat + classifier
bash scripts/main.sh \
  yapwithai/impish-12b-awq \
  yapwithai/yap-longformer-screenshot-intent

# Chat-only AWQ
bash scripts/main.sh chat yapwithai/impish-12b-awq

# GPTQ-only chat deployment
bash scripts/main.sh chat SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32
```

> **Note on llmcompressor / W4A16 exports:** Whether the chat model lives locally or on Hugging Face, the code inspects `quantization_config.json` (and `awq_metadata.json` when present) to pick the correct vLLM backend (e.g., `compressed-tensors` for W4A16/NVFP4 checkpoints). Just set `HF_TOKEN`/`HUGGINGFACE_HUB_TOKEN` for private repos and point `CHAT_MODEL` at the repo ID—no re-quantization step is needed. GPTQ repos are likewise detected automatically and routed through the GPTQ runtime. (Classifier `TOOL_MODEL` repos are loaded via `AutoModelForSequenceClassification` and are never quantized.)

## Local Test Dependencies

If you just want to run the WebSocket test clients (warmup, live, conversation, etc.) on a laptop or CPU-only machine, don’t install the GPU-heavy `requirements.txt`. Instead:

```bash
python3 -m venv .venv-local
source .venv-local/bin/activate
pip install -r requirements-local.txt
```

This installs the lightweight client deps (`websockets`, `httpx`, `orjson`) without pulling CUDA wheels, so macOS users can run `python3 tests/live.py ...` without errors. Use the full `requirements.txt` only when you need to run the actual inference server.

## Test Clients

Highlights:

- [`tests/warmup.py`](ADVANCED.md#warmup-test-client) – one-turn toolcall + chat smoke. Supports `--gender`, `--personality` (alias: `--style`) and honors `SERVER_WS_URL`, `PERSONALITY`, `GENDER`, and `RECV_TIMEOUT_SEC` env vars. Add `--prompt-mode tool` when you deploy *only* the classifier so the client skips chat prompts; otherwise the default `both` sends the chat persona.
- [`tests/live.py`](ADVANCED.md#interactive-live-client) – interactive streaming client that hot-reloads personas from `tests/prompts/live.py`. Requires chat prompts (use `--prompt-mode chat` or `both`).
- [`tests/personality.py`](ADVANCED.md#personality-switch-test) – exercises persona swaps and history stitching to ensure cache hits are preserved. Requires `--prompt-mode chat` or `both` because persona updates depend on chat prompts.
- [`tests/conversation.py`](ADVANCED.md#conversation-history-test) – deterministic 10-turn trace for KV eviction and latency metrics; honors `--prompt-mode` the same way as warmup/live.
- [`tests/screen_analysis.py`](ADVANCED.md#screen-analysis--toolcall-test) – validates the toolcall branch used by screen analysis flows; chat prompts are mandatory.
- [`tests/tool.py`](ADVANCED.md#tool-regression-test) – regression harness for the screenshot/tool-call classifier (timeouts, concurrency, limit flags). `--prompt-mode tool` skips chat prompts (classifier-only), whereas `both`/`chat` also streams the chat response.
- [`tests/bench.py`](ADVANCED.md#benchmark-client) – load generator that reports p50/p95 latencies for sequential sessions.

All of them run on the lightweight `requirements-local.txt` environment described above; check the advanced guide for full command examples.

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
  --tool-model yapwithai/yap-longformer-screenshot-intent \
  --chat-quant fp8

# Classifier-only reset (no chat engine)
bash scripts/restart.sh --reset-models --deploy-mode tool \
  --tool-model yapwithai/yap-longformer-screenshot-intent

# Auto-detect pre-quantized repos (AWQ/GPTQ) during reset
bash scripts/restart.sh --reset-models --deploy-mode chat \
  --chat-model cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit
bash scripts/restart.sh --reset-models --deploy-mode chat \
  --chat-model SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64

# Full stop and restart cycle
bash scripts/stop.sh && bash scripts/main.sh 4bit <chat_model> <tool_model>
```

Key restart knobs:
- `--keep-models` (default) reuses cached AWQ exports; combine with `NUKE_ALL=0` for sub-minute restarts.
- `--reset-models` wipes caches before relaunching different repos or quantization.
- `--install-deps` reinstalls `.venv` before launching.
- `--push-quant` uploads the cached quantized build to HF; see [`ADVANCED.md#pushing-awq-exports-to-hugging-face`](ADVANCED.md#pushing-awq-exports-to-hugging-face) for required env vars.

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