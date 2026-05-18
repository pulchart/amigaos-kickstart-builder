"""Tiny stdout/stderr helpers used everywhere."""

from __future__ import annotations

import sys


def info(msg: str) -> None:
    """Print an informational message to stdout."""
    print(msg)


def die(msg: str, code: int = 1) -> None:
    """Print ``ERROR: <msg>`` to stderr and exit with *code*."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)
