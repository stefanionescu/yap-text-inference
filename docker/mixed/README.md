## Yap Text Inference Mixed Image

Embed-first image that downloads models at build time and runs them as-is. Supports:

- Pre-quantized AWQ models (chat and/or tool)
- Float models (run with fp8 path where applicable)
- Chat-only / Tool-only / Both
- Mixed quant (e.g., chat=AWQ, tool=float)

> ℹ️ AWQ artifacts are the same W4A16 compressed-tensor exports produced by `llmcompressor` (or AutoAWQ 0.2.9 for Qwen2/Qwen3 and Mistral 3). Whether the model lives inside the image or is mounted from Hugging Face, vLLM now auto-detects the `quantization_config.json` metadata and switches to `quantization=compressed-tensors` automatically (so long as `HF_TOKEN`/`HUGGINGFACE_HUB_TOKEN` is provided for private repos).

## Contents

- [Build](#build)
- [Tagging and Variants](#tagging-and-variants)
- [Run](#run)
  - [Run (both embedded)](#run-both-embedded)
  - [Run with overrides](#run-with-overrides)
- [Concurrency](#concurrency)
- [Health](#health)

### Build

Models are embedded at build time. The container does not download or quantize models at runtime.

Quick build and push:

```bash
DOCKER_USERNAME=yourusername DEPLOY_MODELS=both CHAT_MODEL=org/chat TOOL_MODEL=org/tool docker/mixed/build.sh                  # :both-fp8
DOCKER_USERNAME=yourusername DEPLOY_MODELS=both CHAT_MODEL=org/chat-awq TOOL_MODEL=org/tool-awq docker/mixed/build.sh          # :both-awq
DOCKER_USERNAME=yourusername DEPLOY_MODELS=both CHAT_MODEL=org/chat TOOL_MODEL=org/tool-awq docker/mixed/build.sh              # :both-chat-fp8-tool-awq
DOCKER_USERNAME=yourusername DEPLOY_MODELS=both CHAT_MODEL=org/chat-awq TOOL_MODEL=org/tool docker/mixed/build.sh              # :both-chat-awq-tool-fp8
DOCKER_USERNAME=yourusername DEPLOY_MODELS=chat CHAT_MODEL=org/chat docker/mixed/build.sh                                      # :chat-fp8
DOCKER_USERNAME=yourusername DEPLOY_MODELS=chat CHAT_MODEL=org/chat-awq docker/mixed/build.sh                                  # :chat-awq
DOCKER_USERNAME=yourusername DEPLOY_MODELS=tool TOOL_MODEL=org/tool docker/mixed/build.sh                                      # :tool-fp8
DOCKER_USERNAME=yourusername DEPLOY_MODELS=tool TOOL_MODEL=org/tool-awq docker/mixed/build.sh                                  # :tool-awq
```

> **llmcompressor pin:** The Dockerfile installs `llmcompressor==0.8.1` with `--no-deps` so it can coexist with `torch==2.9.0`. Override via `LLMCOMPRESSOR_VERSION=... docker/mixed/build.sh` if you need a different release, but keep the manual install pattern. AutoAWQ (`autoawq==0.2.9`) is also part of the base requirements so Qwen-family models can bypass llmcompressor automatically.

Important: specify exactly one source per engine (chat/tool). Provide either a float/GPTQ repo or a pre-quantized AWQ/W4A16 repo for each engine; detection is automatic.

### Tagging and Variants

Use `TAG` to publish a distinct tag per deployment combo. Examples:

```bash
# Float (both)
TAG=float-both \
DOCKER_USERNAME=yourusername \
DEPLOY_MODELS=both \
CHAT_MODEL=SicariusSicariiStuff/Impish_Nemo_12B \
TOOL_MODEL=MadeAgents/Hammer2.1-3b \
  docker/mixed/build.sh

# Pre-quantized AWQ (both)
TAG=awq-both \
DOCKER_USERNAME=yourusername \
DEPLOY_MODELS=both \
CHAT_MODEL=your-org/chat-awq \
TOOL_MODEL=your-org/tool-awq \
  docker/mixed/build.sh

# Mixed: chat=AWQ, tool=float
TAG=awqchat-toolfloat \
DOCKER_USERNAME=yourusername \
DEPLOY_MODELS=both \
CHAT_MODEL=your-org/chat-awq \
TOOL_MODEL=MadeAgents/Hammer2.1-3b \
  docker/mixed/build.sh

# Chat-only float
TAG=float-chat \
DOCKER_USERNAME=yourusername \
DEPLOY_MODELS=chat \
CHAT_MODEL=SicariusSicariiStuff/Impish_Nemo_12B \
  docker/mixed/build.sh

# Tool-only float
TAG=float-tool \
DOCKER_USERNAME=yourusername \
DEPLOY_MODELS=tool \
TOOL_MODEL=MadeAgents/Hammer2.1-3b \
  docker/mixed/build.sh

# Bake default concurrency (sequential)
TAG=float-both-seq \
DOCKER_USERNAME=yourusername \
DEPLOY_MODELS=both \
CHAT_MODEL=SicariusSicariiStuff/Impish_Nemo_12B \
TOOL_MODEL=MadeAgents/Hammer2.1-3b \
DEFAULT_CONCURRENT=0 \
  docker/mixed/build.sh
```

Preloaded paths (if used):

- Float/GPTQ chat -> `/app/models/chat`
- Float/GPTQ tool -> `/app/models/tool`
- AWQ chat -> `/app/models/chat_awq`
- AWQ tool -> `/app/models/tool_awq`

At runtime, models are used from the embedded paths. No downloads or runtime quantization occur.

### Run

Defaults:

- `DEPLOY_MODELS=both` (if both embedded)
- `CONCURRENT_MODEL_CALL` baked via `DEFAULT_CONCURRENT` at build (override allowed at run)
- `QUANTIZATION` derived from embedded models (both AWQ -> `awq`, else `fp8`)

Runtime environment variables:

- `DEPLOY_MODELS=both|chat|tool`
- `CONCURRENT_MODEL_CALL=0|1`

AWQ push is not performed by the Mixed image (no runtime quantization).

Always pass your API key when running the container:

```bash
docker run -d --gpus all --name yap \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 yourusername/yap-text-inference-mixed:both-fp8
```

#### Run (both embedded)

```bash
docker run -d --gpus all --name yap \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 yourusername/yap-text-inference-mixed:both-fp8
```

#### Run with overrides

```bash
# Chat only
docker run -d --gpus all --name yap-chat \
  -e DEPLOY_MODELS=chat \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 yourusername/yap-text-inference-mixed:chat-fp8

# Tool only
docker run -d --gpus all --name yap-tool \
  -e DEPLOY_MODELS=tool \
  -e TEXT_API_KEY=your_secret_key \
  -p 8000:8000 yourusername/yap-text-inference-mixed:tool-awq
```

Quantization is automatically derived from embedded models (AWQ dirs -> `awq` → detected as compressed tensors; otherwise `fp8`). The server logs show the detected backend and quantizer metadata (llmcompressor vs AutoAWQ) so you can confirm the baked combination.

### Concurrency

- Default is baked at build time via `DEFAULT_CONCURRENT`. You can override with `-e CONCURRENT_MODEL_CALL=0|1` at run.

### Health

```bash
curl -f http://localhost:8000/healthz
```


