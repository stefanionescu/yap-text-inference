#!/usr/bin/env bash

# Final defaults if still unset
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}

# Performance tuning
export CUDA_DEVICE_MAX_CONNECTIONS=${CUDA_DEVICE_MAX_CONNECTIONS:-2}
export PYTORCH_ALLOC_CONF=${PYTORCH_ALLOC_CONF:-expandable_segments:True,garbage_collection_threshold:0.9,max_split_size_mb:512}

# Safety: try to disable DeepGEMM MoE if the package supports it
export TLLM_DISABLE_DEEP_GEMM=${TLLM_DISABLE_DEEP_GEMM:-1}

