#!/usr/bin/env bash

# PyTorch and torchvision compatibility check
# Ensures PyTorch and torchvision are compiled with matching CUDA versions

check_torch_compatibility() {
  local phase="${1:-startup}"
  
  log_info "[${phase}] Checking PyTorch and torchvision compatibility..."
  
  # Run Python check to import torch and torchvision
  # Exit with code 1 only if we detect CUDA version mismatch RuntimeError
  local check_output
  check_output=$(python3 -c "
import sys
try:
    import torch
    import torchvision
    print(f'PyTorch version: {torch.__version__}')
    print(f'torchvision version: {torchvision.__version__}')
    print(f'CUDA available: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'CUDA version: {torch.version.cuda}')
except RuntimeError as e:
    error_msg = str(e)
    if 'CUDA major versions' in error_msg or 'different CUDA' in error_msg:
        print(f'CUDA_MISMATCH: {error_msg}', file=sys.stderr)
        sys.exit(1)
    raise
" 2>&1)
  local exit_code=$?
  
  # If exit code is 1, check if it's a CUDA mismatch
  if [ "${exit_code}" -eq 1 ]; then
    if echo "${check_output}" | grep -q "CUDA_MISMATCH:"; then
      log_err "[${phase}] PyTorch and torchvision CUDA version mismatch detected"
      log_err "[${phase}] $(echo "${check_output}" | grep "CUDA_MISMATCH:" | sed 's/CUDA_MISMATCH: //')"
      log_err "[${phase}] Please reinstall torchvision to match your PyTorch CUDA version"
      log_err "[${phase}] Aborting ${phase} due to incompatible CUDA versions"
      return 1
    fi
  fi
  
  # Success case - log the output
  if [ "${exit_code}" -eq 0 ]; then
    echo "${check_output}" | while IFS= read -r line; do
      log_info "[${phase}] ${line}"
    done
    log_info "[${phase}] PyTorch and torchvision compatibility check passed"
    return 0
  fi
  
  # Other errors (like ImportError) - don't fail here, let it fail later if needed
  log_warn "[${phase}] PyTorch/torchvision check encountered an error (may not be installed yet)"
  return 0
}

