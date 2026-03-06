"""Shared pytest configuration for the repository test suite."""

from __future__ import annotations

import os

# Keep test runs deterministic/noiseless even when developer shells export
# production telemetry credentials.
os.environ["AXIOM_API_TOKEN"] = ""
os.environ["SENTRY_DSN"] = ""
os.environ["OTEL_SDK_DISABLED"] = "true"
