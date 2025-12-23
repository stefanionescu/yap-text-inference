# Yap Text Inference Server

A high-performance text inference server supporting **both vLLM and TensorRT-LLM** engines, optimized for pairing a chat model with a lightweight screenshot-intent classifier. It can run:
- A chat engine (vLLM or TRT-LLM) for roleplay / assistant flows
- A classifier-only tool router (takes screenshots or skips them)
- Either engine independently or both together
- FastAPI + WebSocket streaming

## Contents

- [Key Features](#key-features)
- [Quickstart](#quickstart)
- [Docker Deployment](#docker-deployment)
- [Quantization](#quantization)
  - [vLLM Quantization](#vllm-quantization)
  - [TensorRT-LLM Quantization](#tensorrt-llm-quantization)
  - [Pre-Quantized Models](#pre-quantized-models)
- [Inference Engines](#inference-engines)
- [Local Test Dependencies](#local-test-dependencies)
- [Test Clients](#test-clients)
- [Stopping and Restarting](#stopping-and-restarting)
  - [Stop Script Behavior](#stop-script-behavior)
- [Health Check](#health-check)
- [Advanced Usage and Tips](#advanced-usage-and-tips)

## Key Features
- **Dual-engine support:** Choose between vLLM and TensorRT-LLM based on your deployment needs.
- Chat + classifier deployment with optional chat-only or classifier-only modes.
- Tool-call-first detection: tool decisions fire before chat tokens.
- Persona/history segmented prompts with prefix caching (vLLM) or block reuse (TRT-LLM) for low latency.
- Integrated quantization: AWQ/GPTQ/FP8 for vLLM; INT4-AWQ/FP8/INT8-SQ for TRT-LLM.
- Built-in resiliency: interrupts/barge-in, heartbeats, idle watchdog (150 s default), and sliding-window rate limits.
- Secure multi-tenant guardrails via required API keys and a global semaphore driven by `MAX_CONCURRENT_CONNECTIONS`.

## Quickstart

### Required Environment Variables

Set the compulsory environment variables before invoking any host script:

```bash
export TEXT_API_KEY="my_super_secret_key"    # Required for every API call
export HF_TOKEN="hf_your_api_token"          # Required even for private/gated HF repos
export MAX_CONCURRENT_CONNECTIONS=32         # Required capacity guard
export TRT_MAX_BATCH_SIZE=32                 # Required for TRT: max sequences per forward pass (baked into engine)
```

`HUGGINGFACE_HUB_TOKEN` is also accepted and will be mirrored into `HF_TOKEN` automatically.

1) Install deps and start the server

```bash
# Chat + classifier (default) - auto-detached deployment with log tailing
bash scripts/main.sh [--trt|--vllm] [4bit|8bit] <chat_model> <classifier_model>

# Chat-only / classifier-only helpers (host scripts only; Docker always runs both)
bash scripts/main.sh [--trt|--vllm] [4bit|8bit] chat <chat_model>
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
# TRT-LLM with INT4-AWQ quantization (default engine)
bash scripts/main.sh 4bit SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent

# vLLM with FP8 quantization
bash scripts/main.sh --vllm 8bit SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent

# vLLM with pre-quantized GPTQ model
bash scripts/main.sh --vllm SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64 yapwithai/yap-longformer-screenshot-intent
```

This will:
- Check GPU availability
- Install Python deps from `requirements-trt.txt` or `requirements-vllm.txt`
- Export environment defaults
- For TRT-LLM: Quantize → Build engine → Launch server
- For vLLM: Quantize (if needed) → Launch server
- Always runs in background with auto-detached process isolation
- Auto-tails logs (Ctrl+C stops tail only)

## Docker Deployment

Deploy the server in Docker using the AWQ stack in `docker/`:

```bash
# Build the image
DOCKER_USERNAME=youruser DEPLOY_MODE=both ./docker/build.sh

# Run (chat + classifier)
docker run -d --gpus all --name yap-awq \
  -e DEPLOY_MODE=both \
  -e TOOL_MODEL=yapwithai/yap-longformer-screenshot-intent \
  -e TEXT_API_KEY=your_secret_key \
  -e HF_TOKEN=hf_your_api_token \
  -e MAX_CONCURRENT_CONNECTIONS=32 \
  -p 8000:8000 youruser/yap-text-inference-awq:both

# Chat-only (uses default model: cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit)
DOCKER_USERNAME=youruser DEPLOY_MODE=chat ./docker/build.sh
docker run -d --gpus all --name yap-chat \
  -e DEPLOY_MODE=chat \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 youruser/yap-text-inference-awq:chat

# Classifier-only
DOCKER_USERNAME=youruser DEPLOY_MODE=tool ./docker/build.sh
docker run -d --gpus all --name yap-tool \
  -e DEPLOY_MODE=tool \
  -e TOOL_MODEL=yapwithai/yap-longformer-screenshot-intent \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 youruser/yap-text-inference-awq:tool
```

> Tool classifiers are standard PyTorch weights loaded via `AutoModelForSequenceClassification`. They're cached locally (e.g., `$REPO/.run`, `.hf`, or `/app/models/tool` inside Docker) so restarts reuse them instantly.

See `docker/README.md` for build arguments, image behavior, and run options.

## Quantization

Pass `4bit` or `8bit` to the host scripts. The logs will spell out the actual backend that gets selected so you always know what's running.

### vLLM Quantization

vLLM uses llmcompressor for AWQ/W4A16 quantization (with AutoAWQ fallback for Qwen & Mistral 3):

```bash
# AWQ 4-bit quantization
bash scripts/main.sh --vllm 4bit SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent

# FP8 8-bit quantization (L40S/H100) or INT8 (A100)
bash scripts/main.sh --vllm 8bit SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent
```

Override `AWQ_CALIB_DATASET`, `AWQ_NSAMPLES`, or `AWQ_SEQLEN` to tune the calibration recipe (default dataset: `open_platypus`).

> **AutoAWQ fallback:** Qwen2/Qwen3 and Mistral 3 checkpoints automatically switch to [AutoAWQ 0.2.9](https://github.com/AutoAWQ/AutoAWQ) because llmcompressor cannot yet trace their hybrid forward graphs.

### TensorRT-LLM Quantization

TRT-LLM uses NVIDIA's quantization pipeline with GPU-aware format selection:

```bash
# INT4-AWQ quantization (all GPUs) - TRT_MAX_BATCH_SIZE is required
export TRT_MAX_BATCH_SIZE=32
bash scripts/main.sh --trt 4bit SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent

# 8-bit: FP8 on L40S/H100 (sm89/sm90), INT8-SQ on A100 (sm80)
export TRT_MAX_BATCH_SIZE=16
bash scripts/main.sh --trt 8bit SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent
```

TRT-LLM quantization creates a checkpoint, then builds a compiled `.engine` file. The engine is GPU-architecture specific (e.g., H100 engines won't run on A100).

> **Required:** `TRT_MAX_BATCH_SIZE` must be set when building a TRT engine (including from pre-quantized TRT checkpoints). This value is baked into the engine and determines how many sequences can be batched together. See `ADVANCED.md` for details on batch size configuration.

**MoE models** (e.g., Qwen3-30B-A3B) are automatically detected and quantized with the standard `quantize.py` script.

Override `TRT_CALIB_SIZE`, `TRT_CALIB_SEQLEN`, or `TRT_AWQ_BLOCK_SIZE` to tune calibration.

### Pre-Quantized Models

Both engines auto-detect pre-quantized repos whose names include common markers:
- `awq`, `w4a16`, `nvfp4`, `compressed-tensors`, `autoround`
- `gptq`, `gptq_marlin`
- `trt` + `awq` (TRT-LLM specific)

```bash
# Pre-quantized AWQ chat + classifier (vLLM)
bash scripts/main.sh --vllm yapwithai/impish-12b-awq yapwithai/yap-longformer-screenshot-intent

# Pre-quantized TRT-AWQ (TensorRT-LLM) - still needs TRT_MAX_BATCH_SIZE for engine build
export TRT_MAX_BATCH_SIZE=32
bash scripts/main.sh --trt yapwithai/impish-12b-trt-awq yapwithai/yap-longformer-screenshot-intent

# GPTQ-only chat deployment (vLLM)
bash scripts/main.sh --vllm chat SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32
```

> **Note:** The code inspects `quantization_config.json` (and `awq_metadata.json` when present) to pick the correct backend. Just set `HF_TOKEN`/`HUGGINGFACE_HUB_TOKEN` for private repos—no re-quantization step is needed.

> **TRT pre-quantized models:** These are checkpoints, not pre-built engines. You still need to set `TRT_MAX_BATCH_SIZE` because the engine is built locally from the checkpoint.

## Inference Engines

Yap supports two inference backends:

| Feature | vLLM | TensorRT-LLM |
|---------|------|--------------|
| **Default** | No | **Yes** |
| **Quantization** | AWQ, GPTQ, FP8, INT8 | INT4-AWQ, FP8, INT8-SQ |
| **Memory Management** | Periodic cache reset | Built-in block reuse |
| **Pre-built Engines** | No (JIT) | Yes (compiled .engine) |
| **CUDA Requirement** | 13.x | 13.0+ |
| **PyTorch** | 2.9.x | 2.9.x |
| **MoE Support** | Via FLA | Via quantize.py |

Select the engine with CLI flags or environment variable:

```bash
# TensorRT-LLM (default)
bash scripts/main.sh 4bit <chat_model> <tool_model>
bash scripts/main.sh --trt 4bit <chat_model> <tool_model>

# vLLM
bash scripts/main.sh --vllm 4bit <chat_model> <tool_model>

# Or via environment variable
export INFERENCE_ENGINE=vllm
bash scripts/main.sh 4bit <chat_model> <tool_model>
```

> **Engine switching:** Changing engines (e.g., `--trt` to `--vllm`) triggers a **full environment wipe** including HF caches, pip deps, quantized models, and engine artifacts. This ensures clean state transitions.

## Local Test Dependencies

If you just want to run the WebSocket test clients (warmup, live, conversation, etc.) on a laptop or CPU-only machine, don't install the GPU-heavy requirements. Instead:

```bash
python3 -m venv .venv-local
source .venv-local/bin/activate
pip install -r requirements-local.txt
```

This installs the lightweight client deps (`websockets`, `httpx`, `orjson`) without pulling CUDA wheels, so macOS users can run `python3 tests/live.py ...` without errors. Use `requirements-trt.txt` or `requirements-vllm.txt` only when you need to run the actual inference server.

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
# Light stop (preserve models and dependencies)
NUKE_ALL=0 bash scripts/stop.sh

# Quick restart using existing quantized models (same engine)
bash scripts/restart.sh [both|chat|tool]

# Switch engines during restart (triggers full wipe)
bash scripts/restart.sh --vllm [both|chat|tool]
bash scripts/restart.sh --trt [both|chat|tool]

# Restart and reinstall dependencies (e.g., refresh venv)
bash scripts/restart.sh both --install-deps

# Reset models/quantization without reinstalling deps
bash scripts/restart.sh --reset-models --deploy-mode both \
  --chat-model SicariusSicariiStuff/Impish_Nemo_12B \
  --tool-model yapwithai/yap-longformer-screenshot-intent \
  --chat-quant 8bit

# Classifier-only reset (no chat engine)
bash scripts/restart.sh --reset-models --deploy-mode tool \
  --tool-model yapwithai/yap-longformer-screenshot-intent

# Auto-detect pre-quantized repos (AWQ/GPTQ) during reset
bash scripts/restart.sh --reset-models --deploy-mode chat \
  --chat-model cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit

# Full stop and restart cycle
bash scripts/stop.sh && bash scripts/main.sh --trt 4bit <chat_model> <tool_model>
```

Key restart knobs:
- `--trt` / `--vllm`: Select inference engine (switching triggers full environment wipe).
- `--keep-models` (default) reuses cached exports; combine with `NUKE_ALL=0` for sub-minute restarts.
- `--reset-models` wipes caches before relaunching different repos or quantization.
- `--install-deps` reinstalls `.venv` before launching.
- `--push-quant` uploads the cached quantized build to HF; see [`ADVANCED.md#pushing-quantized-exports-to-hugging-face`](ADVANCED.md#pushing-quantized-exports-to-hugging-face) for required env vars.

Caches are wiped by default during model resets; they are only preserved automatically when the requested models *and* quantization match the previous deployment.

### Stop Script Behavior

Default behavior (`NUKE_ALL=1`, model reset):
- Terminates `uvicorn src.server:app` and engine workers
- **Preserves venv** (pip deps) — hash-based skip logic handles dep updates efficiently
- Clears repo-local caches (`.hf`, `.vllm_cache`, `.trt_cache`, `.awq`, `.torch_inductor`, `.triton`, `.flashinfer`, `.xformers`), tmp (`/tmp/vllm*`, `/tmp/flashinfer*`, `/tmp/torch_*`)
- Clears HF caches, torch caches, NVIDIA PTX JIT cache, and `$HOME/.cache`
- Preserves the repository, the container, and services like Jupyter/web console

Control flags:

```bash
# Light stop (preserve everything including models)
NUKE_ALL=0 bash scripts/stop.sh

# Full wipe including venv (for engine switch or fresh install)
NUKE_VENV=1 bash scripts/stop.sh

# Or combine for maximum cleanup
NUKE_ALL=1 NUKE_VENV=1 bash scripts/stop.sh
```

Note: `--install-deps` and engine switching (`--trt` ↔ `--vllm`) automatically set `NUKE_VENV=1`.

## Health Check

```bash
curl -s http://127.0.0.1:8000/healthz
```

## Advanced Usage and Tips

Looking for logs, TensorRT-LLM configuration, vLLM tuning, WebSocket protocol details, or pushing quantized exports? See `ADVANCED.md`.
