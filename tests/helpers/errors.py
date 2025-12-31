"""Shared exception classes for test clients.

This module defines error types that can be raised when the server
returns error responses. All test scripts should catch these and
exit with non-zero status codes.
"""

from __future__ import annotations


class ServerError(Exception):
    """Raised when the server returns an error message."""

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"{error_code}: {message}")


__all__ = ["ServerError"]

