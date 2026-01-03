"""Execution engines for tool and chat processing.

This package orchestrates the execution flow from user message to response:

executor.py:
    The main sequential tool-then-chat workflow:
    1. Run tool router to detect screenshot intent
    2. Send toolcall response (yes/no) to client
    3. Either dispatch hard-coded control response or stream chat

chat/:
    Chat generation infrastructure:
    - runner.py: High-level generation with sampling params
    - controller.py: Stream buffering, cancellation, timeout handling

tool/:
    Tool/classifier integration:
    - runner.py: Tool call execution with filters
    - filter.py: Screenshot pre-filtering
    - parser.py: Parse tool results from classifier
    - language.py: English detection filter

Workflow Overview:
    User Message -> Tool Filter -> Tool Classifier -> Chat Model -> Response
    
    If tool detects screenshot request:
        Prefix user message with "CHECK SCREEN" and run chat

Import from submodules directly:
    from src.execution.chat.runner import run_chat_generation
    from src.execution.tool.filter import filter_tool_phrase
"""
