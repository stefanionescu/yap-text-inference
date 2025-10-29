# Yap Text Inference Server

A single-process, GPU-accelerated text inference server optimized for low TTFT and steady streaming. It can run:
- vLLM chat engine with chat models ranging from 3B–24B
- Engine for tool-call detection
- Both engines together by default; chat-only/tool-only are supported in host scripts but not in Docker
- FastAPI + WebSocket streaming, Pipecat-friendly

## Key Features
- Tool-call-first detection. Toolcall signal is sent when detected, then (when chat is deployed) chat tokens always stream regardless.
- Persona/history segmented prompts with prefix caching for KV reuse.
- FP8/INT8 KV cache in vLLM to reduce VRAM and speed up decoding.
- Interrupts/barge-in via cancel or a new start.
- Concurrent connection limiting to protect GPU resources (deployment/quantization-aware: non-AWQ → 32 tool-only / 24 chat-only / 16 both; AWQ → 64 tool-only / 40 chat-only / 26 both)
- API key authentication for secure access (configurable, default: "yap_token")

## Quickstart (RunPod or Any CUDA Linux Image)

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

You can deploy the server in Docker using the stacks in `docker/awq` (pre-quantized AWQ) and `docker/fp8` (auto FP8/GPTQ):

```bash
# AWQ (pre-quantized models)
DOCKER_USERNAME=youruser docker/awq/build.sh
docker run -d --gpus all --name yap-awq \
  -e AWQ_CHAT_MODEL=yapwithai/impish-12b-awq \
  -e AWQ_TOOL_MODEL=yapwithai/hammer-2.1-3b-awq \
  -e YAP_TEXT_API_KEY=yap_token \
  -p 8000:8000 youruser/yap-text-inference-awq:latest

# Auto-quant (FP8/GPTQ auto-detect)
DOCKER_USERNAME=youruser docker/fp8/build.sh
docker run -d --gpus all --name yap-auto \
  -e CHAT_MODEL=your-org/float-or-gptq-chat \
  -e TOOL_MODEL=your-org/float-or-gptq-tool \
  -e YAP_TEXT_API_KEY=yap_token \
  -p 8000:8000 youruser/yap-text-inference-auto:latest
```

See `docker/awq/README.md` and `docker/fp8/README.md` for environment variables and advanced options.

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

# Test concurrent mode (restart server first)
# Terminal 1: Start server with concurrent mode (auto → FP8)
bash scripts/stop.sh  # Stop previous deployment
CONCURRENT_MODEL_CALL=1 bash scripts/main.sh SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b

# Terminal 2: Test the same query (after server is ready)
python3 test/warmup.py "write a simple hello world function"

# Test the roleplay-optimized model
# Terminal 1: Start server with Wingless_Imp_8B (auto → FP8)
bash scripts/stop.sh  # Stop previous deployment
bash scripts/main.sh SicariusSicariiStuff/Wingless_Imp_8B MadeAgents/Hammer2.1-1.5b

# Terminal 2: Test creative/roleplay query (after server is ready)
python3 test/warmup.py "*waves hand* Tell me a creative story about a lonely dragon"
```

The concurrent mode should show lower `ttfb_ms` for chat responses where the toolcall model returns false.

### Environment Overrides

- `SERVER_WS_URL` (default `ws://127.0.0.1:8000/ws`)
- `ASSISTANT_GENDER` (default `female`) — aliases accepted: `woman|man`
- `PERSONA_STYLE` (default `wholesome`)
- `RECV_TIMEOUT_SEC` (default `60`)

Examples:

```bash
SERVER_WS_URL=ws://127.0.0.1:8000/ws python3 test/warmup.py
RECV_TIMEOUT_SEC=120 python3 test/warmup.py --gender female --style savage "hey there"
```

### What It Prints

- An ACK line confirming session seed/time and effective `assistant_gender`/`persona_style`.
- Two JSON lines when streaming completes:
  - Metrics: `{ "type": "metrics", "ttfb_ms": ..., "total_ms": ..., "stream_ms": ..., "chunks": ..., "chars": ... }`
  - Final text: `{ "type": "final_text", "text": "..." }`

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

## Advanced Usage

Looking for logs, status/health endpoints, security configuration, restart flows, environment variables, WebSocket protocol details, or pushing AWQ exports? See `ADVANCED.md`.