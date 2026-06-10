"""Argparse front-end and the top-level main() loop."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .build import build_one, preflight
from .config import Cfg
from .errors import die
from .paths import CONFIG_DIR, OUT_DIR

__version__ = "2.1"


_TARGETS_HELP = """\
Available build targets:

  Single model:
    a600             A600  AmigaOS 3.2.3  (same as a600-3.2.3)
    a1200            A1200 AmigaOS 3.2.3  (same as a1200-3.2.3)
    a600-3.2.3       A600  AmigaOS 3.2.3
    a1200-3.2.3      A1200 AmigaOS 3.2.3
    a600-3.1         A600  AmigaOS 3.1
    a1200-3.1        A1200 AmigaOS 3.1
    a600-2.05        A600  AmigaOS 2.05
    a500plus-2.04    A500+ AmigaOS 2.04

  OS family (builds all models for that OS):
    2.04             A500plus-2.04
    2.05             A600-2.05
    2.0x             A600-2.05 + A500plus-2.04
    3.1              A600-3.1  + A1200-3.1
    3.2 / 3.2.3      A600-3.2.3 + A1200-3.2.3
    both             A600-3.2.3 + A1200-3.2.3

  All:
    all              every variant; default when no target is given
"""

_CONFIG_HELP = """\
kickstart.yaml schema reference:

  models:
    Dict keyed by model name.  Required fields per entry:
      os              AmigaOS version string, e.g. "3.2.3"
      cpu             "68000" or "68020"
      sourcerom_crc   CRC of the Capitoline source ROM
      saveprofile     Capitoline saveprofile directive (empty string = none)
      template        Jinja2 template filename under templates/
      amigaos_dir     Path to the AmigaOS installation (must contain ROMs/ and ADFs/)

  modules:
    Ordered list of entries added on top of the stock ROM.  Each entry uses
    exactly one verb; `rom:` is mandatory on every verb except `skip:`.

    Verbs:
      {adf: <adf-path>, adf_path: <inner-path>, rom: "E0"|"F8"}
          Add a library from a specific ADF file (absolute path).
          Consecutive rows sharing the same ADF are collapsed into one loadadf.

      {file: <path>, rom: "E0"|"F8"}
          Copy a file from disk into the ROM bank (added by its basename).

      {replace: <stock-name>, with: <file-path>, rom: "F8"|"E0"}
          Swap a stock F8 module with a file.  rom:"F8" replaces in-place;
          rom:"E0" suppresses the F8 slot and lands the replacement in E0.

      {replace: <stock-name>, adf: <adf-path>, adf_path: <inner>, rom: "F8"|"E0"}
          Same as above but the replacement comes from inside an ADF.

      {skip: <stock-name>}
          Drop a stock F8 module entirely.  No `rom:` field allowed.

      {relocate: <stock-name>, rom: "E0"}
          Move a stock F8 module to E0, keeping its original binary.

    Optional per-entry filters (rows are skipped when they do not match):
      cpu: "68000"|"68020"
      os:  "3.1"|"3.2.3"|"2.05"

    When several rows place the same module, the most specific match wins:
    a row pinning both `os:` and `cpu:` beats one pinning only `cpu:`, which
    beats an unscoped row.  This lets a module land in a different ROM bank per
    OS/CPU from one set of rows.  `skip` always applies (it never competes).

    Row order = order of `add` directives emitted into the Capitoline script.

  Note: adf_path values are case-sensitive (Capitoline does an exact-case
  lookup inside the ADF).  A mismatch causes the build to fail hard.

models / models_from:
  The config file must contain either an inline ``models:`` dict or a
  ``models_from: <relative-path>`` key that points to a separate YAML file
  (resolved relative to the config file's own directory) containing the
  ``models:`` dict.  The latter lets multiple config files share one
  common model definitions file without duplication.
"""


class _PrintAndExit(argparse.Action):
    """argparse action: print a text block and exit."""

    def __init__(self, option_strings, dest, text="", **kw):
        super().__init__(option_strings, dest, nargs=0, **kw)
        self._text = text

    def __call__(self, parser, namespace, values, option_string=None):
        print(self._text, end="")
        parser.exit()


def parse_args(argv: list[str]) -> tuple[list[str], bool, str | None, Path | None, bool]:
    parser = argparse.ArgumentParser(
        prog="kickstart.py",
        description=(
            "Kickstart ROM builder for Amiga 600 / 1200. "
            "Produces 1 MB ROMs with extra modules embedded via Capitoline."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-t",
        "--list-targets",
        action=_PrintAndExit,
        text=_TARGETS_HELP,
        help="list available build targets and exit",
    )
    parser.add_argument(
        "-l",
        "--list-configs",
        action="store_true",
        help="list available config profiles in config/ and exit",
    )
    parser.add_argument(
        "--help-config",
        action=_PrintAndExit,
        text=_CONFIG_HELP,
        help="show config file schema reference and exit",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="all",
        help="which ROM(s) to build (default: all, every variant)",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        metavar="FILE",
        help="config file to use: path, or a shortname like 'iconlib' that resolves to config/iconlib.yaml; if omitted every non-underscore YAML in config/ is built in sequence",
    )
    parser.add_argument(
        "-n",
        "--name",
        default=None,
        metavar="NAME",
        help="basename for output files (default: stem of config filename); requires -c",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="suppress the resident table printed after each build",
    )
    aliases = {
        "a600": ["A600-3.2.3"],
        "a1200": ["A1200-3.2.3"],
        "a600-3.2.3": ["A600-3.2.3"],
        "a1200-3.2.3": ["A1200-3.2.3"],
        "a600-3.1": ["A600-3.1"],
        "a1200-3.1": ["A1200-3.1"],
        "a600-2.05": ["A600-2.05"],
        "a500plus": ["A500plus-2.04"],
        "a500plus-2.04": ["A500plus-2.04"],
        "2.04": ["A500plus-2.04"],
        "2.05": ["A600-2.05"],
        "2.0x": ["A600-2.05", "A500plus-2.04"],
        "3.1": ["A600-3.1", "A1200-3.1"],
        "3.2": ["A600-3.2.3", "A1200-3.2.3"],
        "3.2.3": ["A600-3.2.3", "A1200-3.2.3"],
        "all": ["A600-3.2.3", "A1200-3.2.3", "A600-3.1", "A1200-3.1", "A600-2.05", "A500plus-2.04"],
        "both": ["A600-3.2.3", "A1200-3.2.3"],
        "": ["A600-3.2.3", "A1200-3.2.3"],
    }
    args = parser.parse_args(argv)
    target = args.target.lower()
    if target not in aliases:
        parser.error(
            f"Unknown target '{args.target}'. Try: a600 | a1200 | "
            f"a600-3.2.3 | a1200-3.2.3 | a600-3.1 | a1200-3.1 | "
            f"a600-2.05 | a500plus-2.04 | 2.04 | 2.05 | 3.1 | 3.2.3 | all"
        )
    config_path = _resolve_config_arg(args.config) if args.config else None
    return aliases[target], not args.quiet, args.name, config_path, args.list_configs


def _discover_configs() -> list[Path]:
    """Return sorted list of non-underscore YAML files in config/."""
    return sorted(p for p in CONFIG_DIR.glob("*.yaml") if not p.name.startswith("_"))


def _resolve_config_arg(arg: str) -> Path:
    """Resolve -c/--config: existing path, or shortname under config/."""
    direct = Path(arg)
    if direct.is_file():
        return direct.resolve()
    if "/" not in arg and os.sep not in arg:
        for candidate in (CONFIG_DIR / arg, CONFIG_DIR / f"{arg}.yaml"):
            if candidate.is_file():
                return candidate.resolve()
    return direct.resolve()


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    models, verbose, name_arg, config_path, list_configs = parse_args(argv)
    if list_configs:
        for p in _discover_configs():
            print(p.stem)
        return 0
    if name_arg is not None and config_path is None:
        die("-n / --name requires -c (ambiguous across multiple configs)")
    config_paths = [config_path] if config_path is not None else _discover_configs()
    if not config_paths:
        die(f"No config files found in {CONFIG_DIR}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for cp in config_paths:
        if not cp.is_file():
            die(f"Config file not found: {cp}")
        cfg = Cfg.load(cp)
        name = name_arg if name_arg is not None else cp.stem
        preflight(cfg, models)
        for m in models:
            build_one(cfg, m, verbose=verbose, name=name)
    return 0
