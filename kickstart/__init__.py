"""Kickstart ROM builder.

Package entry point: ``./kickstart.py`` script forwards to ``kickstart.cli.main``.
"""

from __future__ import annotations

from .cli import _discover_configs, _resolve_config_arg, main, parse_args
from .config import AdfGroup, Cfg, FileEntry, SourceRomEntry
from .residents import _annotate_residents, _print_residents, scan_residents

__version__ = "1.4"

__all__ = [
    "AdfGroup",
    "Cfg",
    "FileEntry",
    "SourceRomEntry",
    "__version__",
    "_annotate_residents",
    "_discover_configs",
    "_print_residents",
    "_resolve_config_arg",
    "main",
    "parse_args",
    "scan_residents",
]
