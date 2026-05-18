"""YAML config loading and the active-config dataclass."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class FileEntry:
    name: str
    kind: str = "file"


@dataclass
class AdfGroup:
    adf_ref: str
    libs: list[str]
    kind: str = "adf_group"


@dataclass
class SourceRomEntry:
    """Stock module pulled from `$SOURCEROM`, used by `relocate` rows to
    place a stock F8 module into the E0 ROM (template emits
    `add "$SOURCEROM" <name>` in the E0 section)."""

    name: str
    kind: str = "from_source_rom"


def _load_config(path: Path) -> dict:
    """Load a kickstart YAML config file.

    Convert YAML strings to native Python types where useful (amigaos_dir
    becomes a Path).  Everything else stays as-is and is consumed downstream.
    """
    cfg = yaml.safe_load(path.read_text())
    if "models_from" in cfg:
        models_path = (path.parent / cfg["models_from"]).resolve()
        if not models_path.is_file():
            sys.exit(f"ERROR: models_from: '{cfg['models_from']}' not found: {models_path}")
        cfg["models"] = yaml.safe_load(models_path.read_text())["models"]
    cfg.setdefault("modules", [])
    for m in cfg["models"].values():
        m["amigaos_dir"] = Path(m["amigaos_dir"])
    return cfg


@dataclass(frozen=True)
class Cfg:
    """Active build configuration: which YAML is loaded and its parsed contents."""

    yaml_path: Path
    config: dict
    models: dict

    @classmethod
    def load(cls, path: Path) -> Cfg:
        config = _load_config(path)
        return cls(yaml_path=path, config=config, models=config["models"])
