"""File-descriptor level stdout/stderr suppression."""

from __future__ import annotations

import os
import sys
import contextlib


class SuppressedFDContext:
    """Suppress C/C++ stdout/stderr by redirecting process file descriptors."""

    def __init__(self, suppress_stdout: bool = True, suppress_stderr: bool = True):
        self._suppress_stdout = suppress_stdout
        self._suppress_stderr = suppress_stderr
        self._saved_stdout_fd: int | None = None
        self._saved_stderr_fd: int | None = None
        self._devnull: int | None = None

    def __enter__(self) -> SuppressedFDContext:
        sys.stdout.flush()
        sys.stderr.flush()
        with contextlib.suppress(Exception):
            import ctypes  # noqa: PLC0415

            libc = ctypes.CDLL(None)
            libc.fflush(None)

        self._devnull = os.open(os.devnull, os.O_WRONLY)
        if self._suppress_stdout:
            self._saved_stdout_fd = os.dup(1)
            os.dup2(self._devnull, 1)
        if self._suppress_stderr:
            self._saved_stderr_fd = os.dup(2)
            os.dup2(self._devnull, 2)
        return self

    def __exit__(self, *args) -> None:
        with contextlib.suppress(Exception):
            import ctypes  # noqa: PLC0415

            libc = ctypes.CDLL(None)
            libc.fflush(None)

        sys.stdout.flush()
        sys.stderr.flush()

        if self._saved_stdout_fd is not None:
            os.dup2(self._saved_stdout_fd, 1)
            os.close(self._saved_stdout_fd)

        if self._saved_stderr_fd is not None:
            os.dup2(self._saved_stderr_fd, 2)
            os.close(self._saved_stderr_fd)

        if self._devnull is not None:
            os.close(self._devnull)


__all__ = ["SuppressedFDContext"]
