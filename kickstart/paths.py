"""Filesystem locations and ROM-bank constants used across the package."""

from __future__ import annotations

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPT_DIR

CAPITOLINE_DIR = Path("/opt/Capitoline")
CAPCLI = CAPITOLINE_DIR / "capcli.Linux"

# Read-only after install: bundled next to the package, found via SCRIPT_DIR.
CONFIG_DIR = SCRIPT_DIR / "config"
TEMPLATES_DIR = SCRIPT_DIR / "templates"
KICKSTART_YAML = CONFIG_DIR / "cfd.yaml"

# Writable at runtime: relative to the user's CWD so a packaged install
# (where SCRIPT_DIR is /usr/share/...) writes ROMs where the user runs.
OUT_DIR = Path("out")

VALID_ROMS = ("E0", "F8")
