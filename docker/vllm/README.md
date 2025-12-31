# vLLM Docker Image

Pre-quantized vLLM inference image with models baked in at build time.

## Contents

- [Quick Start](#quick-start)
- [Build Variables](#build-variables)
- [Runtime Variables](#runtime-variables)
- [Directory Structure](#directory-structure)

## Quick Start

### Build

```bash
ENGINE=vllm \
  DOCKER_USERNAME=myuser \
  DEPLOY_MODE=chat \
  CHAT_MODEL=cpatonn/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit \
  TAG=vllm-qwen30b-awq \
  bash docker/build.sh
```

### Run

```bash
docker run -d --gpus all --name yap-server \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 \
  myuser/yap-text-api:vllm-qwen30b-awq
```

## Build Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DOCKER_USERNAME` | Yes | Docker Hub username |
| `DEPLOY_MODE` | Yes | `chat`, `tool`, or `both` |
| `CHAT_MODEL` | If chat/both | Pre-quantized HF model (AWQ/GPTQ/W4A16) |
| `TOOL_MODEL` | If tool/both | Tool classifier HF repo |
| `TAG` | Yes | Image tag (must start with `vllm-`) |
| `HF_TOKEN` | If private | HuggingFace token |

## Runtime Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEXT_API_KEY` | Required | API key for authentication |
| `CHAT_GPU_FRAC` | 0.90 | GPU memory fraction for chat model |
| `TOOL_GPU_FRAC` | 0.20 | GPU memory fraction for tool classifier |
| `KV_DTYPE` | auto | KV cache dtype (fp8, int8, auto) |
| `VLLM_USE_V1` | 1 | Use vLLM V1 engine |

## Directory Structure

```
vllm/
├── Dockerfile              # Multi-stage build for vLLM
├── build.sh                # Build and push script
├── download/
│   └── download_chat.py    # Downloads chat model from HF
└── scripts/
    ├── bootstrap.sh        # Runtime environment setup
    ├── main.sh             # Container entrypoint
    ├── start_server.sh     # Server startup
    ├── warmup.sh           # Health check wrapper
    ├── logs.sh             # Logging utilities wrapper
    ├── build/              # Build-time scripts
    │   ├── context.sh      # Build context preparation
    │   └── validate.sh     # Model validation
    └── env/                # Environment configuration
```

The `download/download_tool.py` is sourced from `docker/common/` at build time.

