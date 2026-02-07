"""Yap Text Inference Server Package.

This package provides a high-performance inference server for text generation,
supporting both vLLM and TensorRT-LLM backends. The server handles:

- WebSocket-based real-time chat interactions
- Tool call routing (screenshot intent detection)
- Session management with conversation history
- Model quantization (AWQ, GPTQ, FP8)
- Prefix caching for improved latency

Architecture Overview:
    - server.py: FastAPI application entry point
    - config/: Configuration modules (environment-based)
    - engines/: Inference engine abstractions (vLLM, TRT-LLM)
    - execution/: Request execution pipeline (chat, tool routing)
    - handlers/: WebSocket and session management
    - messages/: Message type handlers (start, followup, cancel)
    - classifier/: Lightweight screenshot intent classifier
    - tokens/: Tokenization utilities
    - helpers/: Shared utility functions

Example:
    Start the server with uvicorn:

    $ uvicorn src.server:app --host 0.0.0.0 --port 8000

Environment Variables:
    Required:
        - MAX_CONCURRENT_CONNECTIONS: Maximum WebSocket connections
        - TEXT_API_KEY: API key for authentication
        - CHAT_MODEL: HuggingFace model ID for chat
          (must include quantization type in name, e.g. '-awq', '-gptq', '-fp8')

    Optional:
        - CHAT_QUANTIZATION: Override auto-detected quantization (awq, gptq, fp8)
        - DEPLOY_MODE: 'both', 'chat', or 'tool' (default: 'both')
        - INFERENCE_ENGINE: 'vllm' or 'trt' (default: 'trt')
        - TOOL_MODEL: Classifier model for tool routing
"""
