"""Test helper package namespace.

This package intentionally avoids eager re-export imports to prevent circular
initialization across `tests.support.helpers` and `tests.support.state`.
"""
