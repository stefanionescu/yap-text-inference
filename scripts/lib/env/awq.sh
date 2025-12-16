#!/usr/bin/env bash

# AWQ-related environment (HF push, repo defaults, model URLs)
# Push is controlled by --push-quant flag (sets HF_AWQ_PUSH=1)
# Validation is done early in main.sh/restart.sh via validate_push_quant_prereqs()

apply_awq_env() {
  # Hugging Face upload controls for AWQ builds
  # HF_AWQ_PUSH is set by --push-quant flag in args.sh, not here
  export HF_AWQ_CHAT_REPO=${HF_AWQ_CHAT_REPO:-"your-org/chat-awq"}
  export HF_AWQ_BRANCH=${HF_AWQ_BRANCH:-main}
  export HF_AWQ_PRIVATE=${HF_AWQ_PRIVATE:-1}
  export HF_AWQ_ALLOW_CREATE=${HF_AWQ_ALLOW_CREATE:-1}
  export HF_AWQ_COMMIT_MSG_CHAT=${HF_AWQ_COMMIT_MSG_CHAT:-}

  # Note: HF_AWQ_PUSH prereqs are validated early in main.sh/restart.sh
  # via validate_push_quant_prereqs() - no need to check again here
}


