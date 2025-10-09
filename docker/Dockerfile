# Multi-stage build for efficient Docker image
FROM nvidia/cuda:12.8-cudnn-devel-ubuntu22.04 AS builder

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"
ENV FORCE_CUDA=1
ENV MAX_JOBS=8

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    git \
    wget \
    curl \
    gcc \
    g++ \
    make \
    cmake \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

# Create Python virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Production stage
FROM nvidia/cuda:12.8-cudnn-runtime-ubuntu22.04

# Set environment variables for production
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create app directory
WORKDIR /app

# Copy application code
COPY src/ /app/src/
COPY prompts.py /app/
COPY docker/scripts/ /app/scripts/

# Create necessary directories
RUN mkdir -p /app/logs /app/.run /app/.hf /app/.vllm_cache

# Set proper permissions
RUN chmod +x /app/scripts/*.sh

# Default environment variables for AWQ deployment
ENV QUANTIZATION=awq
ENV DEPLOY_MODELS=both
ENV CONCURRENT_MODEL_CALL=1
ENV YAP_API_KEY=yap_token
ENV WARMUP_ON_START=1

# GPU-specific optimizations
ENV CUDA_DEVICE_MAX_CONNECTIONS=1
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
ENV VLLM_USE_V1=1
ENV KV_DTYPE=fp8
ENV VLLM_ATTENTION_BACKEND=FLASHINFER
ENV ENFORCE_EAGER=0

# Cache directories
ENV HF_HOME=/app/.hf
ENV TRANSFORMERS_CACHE=/app/.hf
ENV HUGGINGFACE_HUB_CACHE=/app/.hf/hub
ENV VLLM_CACHE_DIR=/app/.vllm_cache

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Default command
CMD ["/app/scripts/main.sh"]
