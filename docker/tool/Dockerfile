# Lightweight single-stage build for tool-only deployment
# Only needs PyTorch + transformers
FROM nvidia/cuda:13.0.0-cudnn-runtime-ubuntu24.04

# Model configuration - set at build time
ARG DEPLOY_MODE="tool"
ARG TOOL_MODEL=""

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"

# Install system dependencies (minimal - no build tools needed)
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    python3-pip \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create Python virtual environment
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Configured models
ENV DEPLOY_MODE=${DEPLOY_MODE}
ENV CHAT_MODEL=""
ENV TOOL_MODEL=${TOOL_MODEL}
ENV CHAT_QUANTIZATION=""

# Engine type
ENV INFERENCE_ENGINE=vllm

# Default directories for baked-in models
ENV MODELS_DIR=/opt/models
ENV CHAT_MODEL_PATH=/opt/models/chat
ENV TOOL_MODEL_PATH=/opt/models/tool

# Create app directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/logs /app/.run /app/.hf /opt/models/tool

# Cache directories
ENV HF_HOME=/app/.hf
ENV HUGGINGFACE_HUB_CACHE=/app/.hf/hub
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    GIT_SSL_CAINFO=/etc/ssl/certs/ca-certificates.crt

# ----------------------------------------------------------------------------
# Copy download scripts (used during build only)
# ----------------------------------------------------------------------------
COPY common/download/ /app/common/download/
RUN chmod +x /app/common/download/*.py 2>/dev/null || true

# ----------------------------------------------------------------------------
# Download tool model at build time (baked into image)
# ----------------------------------------------------------------------------
RUN --mount=type=secret,id=hf_token,required=false \
    python /app/common/download/tool.py

# Override model env var to point to local path
ENV TOOL_MODEL=/opt/models/tool

# Enable all logs in Docker
ENV SHOW_HF_LOGS=1 \
    SHOW_TOOL_LOGS=1

# ----------------------------------------------------------------------------
# Copy application code last (changes frequently, won't invalidate download cache)
# ----------------------------------------------------------------------------
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY common/scripts/ /app/common/scripts/

# Clean up build-time-only download scripts and set proper permissions
RUN rm -rf /app/common/download \
    && chmod +x /app/scripts/*.sh /app/scripts/**/*.sh /app/common/scripts/*.sh 2>/dev/null || true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Default command
CMD ["/app/scripts/main.sh"]

LABEL org.opencontainers.image.title="Yap Text Inference Tool-Only (CUDA 13.0, Py312)" \
      org.opencontainers.image.description="Lightweight tool-only inference image. No chat engine required." \
      org.opencontainers.image.source="https://github.com/Yap-With-AI/yap-text-inference"
