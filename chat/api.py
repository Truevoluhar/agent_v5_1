"""Compatibility chat app wrapper.

The primary HTTP/SSE chat surface lives behind the `chat` package so the
runtime, chat UI, and data browser can evolve as separate app sources while
still reusing the existing service implementation.
"""

from service.api import app, main

__all__ = ["app", "main"]
