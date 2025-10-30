#!/usr/bin/env bash

# AWQ-related environment (HF push, repo defaults, model URLs)

apply_awq_env() {
  # Hugging Face upload controls for AWQ builds
  export HF_AWQ_PUSH=${HF_AWQ_PUSH:-0}
  export HF_AWQ_CHAT_REPO=${HF_AWQ_CHAT_REPO:-"your-org/chat-awq"}
  export HF_AWQ_TOOL_REPO=${HF_AWQ_TOOL_REPO:-"your-org/tool-awq"}
  export HF_AWQ_BRANCH=${HF_AWQ_BRANCH:-main}
  export HF_AWQ_PRIVATE=${HF_AWQ_PRIVATE:-1}
  export HF_AWQ_ALLOW_CREATE=${HF_AWQ_ALLOW_CREATE:-1}
  export HF_AWQ_COMMIT_MSG_CHAT=${HF_AWQ_COMMIT_MSG_CHAT:-}
  export HF_AWQ_COMMIT_MSG_TOOL=${HF_AWQ_COMMIT_MSG_TOOL:-}

  # Pre-quantized AWQ model URLs (alternative to local quantization)
  export AWQ_CHAT_MODEL=${AWQ_CHAT_MODEL:-}
  export AWQ_TOOL_MODEL=${AWQ_TOOL_MODEL:-}

  if [ "${HF_AWQ_PUSH}" = "1" ]; then
    if [ -z "${HF_TOKEN:-}" ]; then
      log_warn "HF_AWQ_PUSH=1 but HF_TOKEN is not set. Aborting."
      return 1
    fi
    if [ "${DEPLOY_CHAT}" = "1" ]; then
      if [ -z "${HF_AWQ_CHAT_REPO}" ] || [[ "${HF_AWQ_CHAT_REPO}" == your-org/* ]]; then
        log_warn "HF_AWQ_PUSH=1 requires HF_AWQ_CHAT_REPO to be set for chat deployments. Aborting."
        return 1
      fi
    fi
    if [ "${DEPLOY_TOOL}" = "1" ]; then
      if [ -z "${HF_AWQ_TOOL_REPO}" ] || [[ "${HF_AWQ_TOOL_REPO}" == your-org/* ]]; then
        log_warn "HF_AWQ_PUSH=1 requires HF_AWQ_TOOL_REPO to be set for tool deployments. Aborting."
        return 1
      fi
    fi
  fi
}


