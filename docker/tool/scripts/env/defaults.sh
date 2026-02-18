#!/usr/bin/env bash
# Tool-only fallback defaults.
#
# Minimal: no engine-specific tuning needed.
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
