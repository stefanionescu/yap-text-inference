"""Ensure project-wide site customizations run for every Python invocation."""

from __future__ import annotations

from src.scripts import site_customize as _site_customize  # noqa: F401

__all__ = getattr(_site_customize, "__all__", [])
