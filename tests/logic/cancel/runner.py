"""Cancel test suite runner for multi-client request cancellation verification.

This module provides the public entry point for the cancel test suite.
It orchestrates multiple concurrent clients where one cancels mid-request
and the others complete normally.

Test flow:
- 1 client: start -> wait -> cancel -> drain (verify silence) -> recovery
- N-1 clients: start -> stream full response -> wait for cancel recovery
- All clients disconnect after coordination
"""

from __future__ import annotations

import uuid
import asyncio
from typing import cast

from tests.helpers.prompt import select_chat_prompt
from tests.helpers.fmt import dim, red, bold, green, section_header
from tests.state import SessionContext, CancelClientResult, NormalClientResult
from tests.config import (
    CANCEL_POST_WAIT_DEFAULT,
    CANCEL_NUM_CLIENTS_DEFAULT,
    CANCEL_RECV_TIMEOUT_DEFAULT,
    CANCEL_DRAIN_TIMEOUT_DEFAULT,
    CANCEL_DELAY_BEFORE_CANCEL_DEFAULT,
)

from .clients import run_normal_client, run_canceling_client
from .output import CANCEL_TEST_MESSAGE, print_cancel_client_result, print_normal_client_results


async def run_cancel_suite(
    ws_url: str,
    *,
    gender: str,
    personality: str,
    num_clients: int = CANCEL_NUM_CLIENTS_DEFAULT,
    cancel_delay_s: float = CANCEL_DELAY_BEFORE_CANCEL_DEFAULT,
    drain_timeout_s: float = CANCEL_DRAIN_TIMEOUT_DEFAULT,
    post_cancel_wait_s: float = CANCEL_POST_WAIT_DEFAULT,
    recv_timeout_s: float = CANCEL_RECV_TIMEOUT_DEFAULT,
) -> bool:
    """Run the multi-client cancel test suite.

    Spawns num_clients concurrent connections:
    - 1 client cancels after cancel_delay_s, verifies no spurious messages, then recovers
    - (num_clients - 1) clients complete inference normally

    All normal clients wait for the canceling client's recovery to complete before
    disconnecting, ensuring proper coordination.

    Args:
        ws_url: WebSocket URL with API key.
        gender: Persona gender for test messages.
        personality: Persona personality style.
        num_clients: Number of concurrent clients (default 3).
        cancel_delay_s: Seconds to wait before sending cancel (default 1.0).
        drain_timeout_s: Seconds to verify no spurious messages (default 2.0).
        post_cancel_wait_s: Seconds to wait after drain before recovery (default 2.0).
        recv_timeout_s: Timeout for each receive phase (default 30.0).

    Returns:
        True if all tests passed, False otherwise.
    """
    print(f"\n{section_header('CANCEL TEST')}")
    display_url = ws_url.split("?")[0]
    print(dim(f"  server: {display_url}"))
    print(dim(f"  persona: {personality}/{gender}"))
    print(dim(f"  clients: {num_clients} (1 cancel, {num_clients - 1} normal)\n"))

    chat_prompt = select_chat_prompt(gender)

    # Event for coordinating normal clients
    recovery_done = asyncio.Event()

    # Create session context for the canceling client
    cancel_ctx = SessionContext(
        session_id=str(uuid.uuid4()),
        gender=gender,
        personality=personality,
        chat_prompt=chat_prompt,
    )

    # Create tasks
    print(f"{bold('▶ STARTING CLIENTS')}")

    cancel_task = asyncio.create_task(
        run_canceling_client(
            ws_url,
            cancel_ctx,
            CANCEL_TEST_MESSAGE,
            cancel_delay_s,
            drain_timeout_s,
            post_cancel_wait_s,
            recv_timeout_s,
            recovery_done,
        )
    )

    normal_tasks = []
    for i in range(num_clients - 1):
        normal_ctx = SessionContext(
            session_id=str(uuid.uuid4()),
            gender=gender,
            personality=personality,
            chat_prompt=chat_prompt,
        )
        task = asyncio.create_task(
            run_normal_client(
                ws_url,
                normal_ctx,
                client_id=i + 1,
                user_msg=CANCEL_TEST_MESSAGE,
                recv_timeout=recv_timeout_s,
                wait_for_recovery=recovery_done,
            )
        )
        normal_tasks.append(task)

    # Run all tasks concurrently
    all_results = await asyncio.gather(cancel_task, *normal_tasks)
    cancel_result = cast(CancelClientResult, all_results[0])
    normal_results = cast(list[NormalClientResult], list(all_results[1:]))

    # Print results
    print(f"\n{bold('▶ CANCEL CLIENT RESULTS')}")
    cancel_passed, cancel_failed = print_cancel_client_result(cancel_result)

    if normal_results:
        print(f"\n{bold('▶ NORMAL CLIENT RESULTS')}")
        normal_passed, normal_failed = print_normal_client_results(normal_results)
    else:
        normal_passed, normal_failed = 0, 0

    # Summary
    total_passed = cancel_passed + normal_passed
    total_failed = cancel_failed + normal_failed
    total = total_passed + total_failed

    print(f"\n{dim('─' * 40)}")
    if total_failed == 0:
        print(f"  {green('All')} {total} tests passed")
    else:
        print(f"  {total_passed} passed, {red(str(total_failed))} failed")

    return total_failed == 0


__all__ = ["run_cancel_suite"]
