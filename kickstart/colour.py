"""Terminal colour helpers; auto-disabled when stdout is not a tty."""

from __future__ import annotations

import sys

_COLOR = sys.stdout.isatty()

_BOLD = "\033[1m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[94m"
_RED = "\033[31m"


def _c(text: str, *codes: str) -> str:
    """Wrap *text* in ANSI escape *codes*; no-op when stdout is not a tty."""
    if not _COLOR:
        return text
    return "".join(codes) + text + "\033[0m"
