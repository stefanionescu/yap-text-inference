## Yap Text Inference Base Image

General-purpose image that mirrors `scripts/` behavior: installs deps, can preload models at build-time, and supports these runtime combinations:

- Pre-quantized AWQ models
- Chat AWQ + float/GPTQ tool
- Chat only / Tool only
- Float or GPTQ chat+tool (no AWQ)
- Optional: quantize float models to AWQ at runtime, with optional push to Hugging Face

### Build

Build-time preloading is optional. You can embed the models into the image to avoid network during `docker run`.

Important: specify exactly one source per engine (chat/tool). Do not set both `CHAT_MODEL` and `AWQ_CHAT_MODEL` for chat, nor both `TOOL_MODEL` and `AWQ_TOOL_MODEL` for tool.

Float/GPTQ preload example (both engines):

```bash
docker build -t yap-text-base \
  --build-arg PRELOAD_MODELS=1 \                                  # 0|1 (default 0)
  --build-arg DEPLOY_MODELS=both \                                # both|chat|tool (preload scope)
  --build-arg CHAT_MODEL=SicariusSicariiStuff/Impish_Nemo_12B \   # float/GPTQ repo
  --build-arg TOOL_MODEL=MadeAgents/Hammer2.1-3b \                # float/GPTQ repo
  --build-arg HF_TOKEN= \                                         # optional HF token for private repos
  -f docker/base/Dockerfile .
```

Pre-quantized AWQ preload example (both engines):

```bash
docker build -t yap-text-base \
  --build-arg PRELOAD_MODELS=1 \                                  # 0|1 (default 0)
  --build-arg DEPLOY_MODELS=both \                                # both|chat|tool (preload scope)
  --build-arg AWQ_CHAT_MODEL=your-org/chat-awq \                  # AWQ repo
  --build-arg AWQ_TOOL_MODEL=your-org/tool-awq \                  # AWQ repo
  --build-arg HF_TOKEN= \                                         # optional HF token for private repos
  -f docker/base/Dockerfile .
```

Mixed preload example (chat AWQ, tool float):

```bash
docker build -t yap-text-base \
  --build-arg PRELOAD_MODELS=1 \
  --build-arg DEPLOY_MODELS=both \
  --build-arg AWQ_CHAT_MODEL=your-org/chat-awq \                  # AWQ chat
  --build-arg TOOL_MODEL=MadeAgents/Hammer2.1-3b \                # float tool
  -f docker/base/Dockerfile .
```

Preloaded paths (if used):

- Float/GPTQ chat -> `/app/models/chat`
- Float/GPTQ tool -> `/app/models/tool`
- AWQ chat -> `/app/models/chat_awq`
- AWQ tool -> `/app/models/tool_awq`

At runtime, if you do not provide `CHAT_MODEL`/`TOOL_MODEL`, the container will use the corresponding preloaded paths (if present). Continue to specify only one source per engine.

### Run

Defaults:

- `DEPLOY_MODELS=both`
- `CONCURRENT_MODEL_CALL=1` (concurrent). Set `CONCURRENT_MODEL_CALL=0` for sequential mode.
- `QUANTIZATION=auto` unless pre-quantized AWQ is present.

Common environment variables:

- `CHAT_MODEL`, `TOOL_MODEL`: HF repo IDs or local paths for float/GPTQ
- `AWQ_CHAT_MODEL`, `AWQ_TOOL_MODEL`: HF repo IDs for pre-quantized AWQ
- `DEPLOY_MODELS=both|chat|tool`
- `QUANTIZATION=auto|fp8|gptq_marlin|awq`
- `CONCURRENT_MODEL_CALL=0|1`

AWQ push controls (only used when `QUANTIZATION=awq` and local quantization is performed):

- `HF_AWQ_PUSH=1`
- `HF_TOKEN=hf_...`
- `HF_AWQ_CHAT_REPO=org/chat-awq`, `HF_AWQ_TOOL_REPO=org/tool-awq`
- Optional: `HF_AWQ_BRANCH`, `HF_AWQ_PRIVATE=1`, `HF_AWQ_ALLOW_CREATE=1`, `HF_AWQ_COMMIT_MSG_CHAT`, `HF_AWQ_COMMIT_MSG_TOOL`

#### Pre-quantized AWQ (both)

```bash
docker run -d --gpus all --name yap \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e AWQ_TOOL_MODEL=your-org/tool-awq \
  -p 8000:8000 yap-text-base
```

#### Chat AWQ + Tool float

```bash
docker run -d --gpus all --name yap \
  -e AWQ_CHAT_MODEL=your-org/chat-awq \
  -e TOOL_MODEL=MadeAgents/Hammer2.1-3b \
  -p 8000:8000 yap-text-base
```

#### Chat only / Tool only

```bash
# Chat only
docker run -d --gpus all --name yap-chat \
  -e DEPLOY_MODELS=chat \
  -e CHAT_MODEL=SicariusSicariiStuff/Impish_Nemo_12B \
  -p 8000:8000 yap-text-base

# Tool only
docker run -d --gpus all --name yap-tool \
  -e DEPLOY_MODELS=tool \
  -e TOOL_MODEL=MadeAgents/Hammer2.1-3b \
  -p 8000:8000 yap-text-base
```

#### Float/GPTQ chat+tool (no AWQ)

```bash
docker run -d --gpus all --name yap \
  -e CHAT_MODEL=SicariusSicariiStuff/Impish_Nemo_12B \
  -e TOOL_MODEL=MadeAgents/Hammer2.1-3b \
  -p 8000:8000 yap-text-base
```

#### Quantize float models to AWQ at runtime

```bash
docker run -d --gpus all --name yap-awq \
  -e QUANTIZATION=awq \
  -e DEPLOY_MODELS=both \
  -e CHAT_MODEL=SicariusSicariiStuff/Impish_Nemo_12B \
  -e TOOL_MODEL=MadeAgents/Hammer2.1-3b \
  -p 8000:8000 yap-text-base
```

Optionally push resulting AWQ dirs to HF:

```bash
docker run -d --gpus all --name yap-awq \
  -e QUANTIZATION=awq -e HF_AWQ_PUSH=1 -e HF_TOKEN=hf_... \
  -e HF_AWQ_CHAT_REPO=org/chat-awq -e HF_AWQ_TOOL_REPO=org/tool-awq \
  -e CHAT_MODEL=SicariusSicariiStuff/Impish_Nemo_12B \
  -e TOOL_MODEL=MadeAgents/Hammer2.1-3b \
  -p 8000:8000 yap-text-base
```

### Concurrency

- Default: concurrent (`CONCURRENT_MODEL_CALL=1`). Set `CONCURRENT_MODEL_CALL=0` for sequential mode.

### Health

```bash
curl -f http://localhost:8000/healthz
```


