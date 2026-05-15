#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Jaroslav Pulchart
import sys
import argparse
import hashlib
import os
import re
import shutil
import struct
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


def _check_requirements() -> None:
    """Exit with a helpful message if Python is too old or any package is missing."""
    if sys.version_info < (3, 10):
        sys.exit(
            f"kickstart.py requires Python 3.10+ "
            f"(running on {sys.version.split()[0]})."
        )
    missing = []
    for pkg, inst in [
        ("yaml",     "pyyaml"),
        ("jinja2",   "jinja2"),
        ("tabulate", "tabulate"),
    ]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(f"  {pkg:<12}")
    if missing:
        sys.exit("Missing required packages:\n" + "\n".join(missing))


_check_requirements()

import yaml
from jinja2 import Environment, FileSystemLoader
from tabulate import tabulate

# ---------------------------------------------------------------------------
# Terminal colour helpers (auto-disabled when stdout is not a tty)
# ---------------------------------------------------------------------------
_COLOR = sys.stdout.isatty()


def _c(text: str, *codes: str) -> str:
    if not _COLOR:
        return text
    return "".join(codes) + text + "\033[0m"


_BOLD   = "\033[1m"
_CYAN   = "\033[36m"
_YELLOW = "\033[33m"

__version__ = "1.1"
__author__ = "Jaroslav Pulchart"
__license__ = "MIT"

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR

CAPITOLINE_DIR = Path("/opt/Capitoline")
CAPCLI = CAPITOLINE_DIR / "capcli.Linux"

CONFIG_DIR = SCRIPT_DIR / "config"
TEMPLATES_DIR = SCRIPT_DIR / "templates"
KICKSTART_YAML = CONFIG_DIR / "kickstart.yaml"
OUT_DIR = SCRIPT_DIR / "out"

VALID_ROMS = ("E0", "F8")


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


def _load_config() -> dict:
    """Load kickstart.yaml once at module init.

    Convert YAML strings to native Python types where useful (amigaos_dir
    becomes a Path).  Everything else stays as-is and is consumed downstream.
    """
    cfg = yaml.safe_load(KICKSTART_YAML.read_text())
    for m in cfg["models"].values():
        m["amigaos_dir"] = Path(m["amigaos_dir"])
    return cfg


CONFIG = _load_config()
MODELS = CONFIG["models"]


def info(msg: str) -> None:
    print(msg)


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def preflight(models: list[str]) -> None:
    if not (CAPCLI.is_file() and os.access(CAPCLI, os.X_OK)):
        die(f"Missing {CAPCLI}")
    if not (CAPITOLINE_DIR / "Components").is_dir():
        die(f"Missing {CAPITOLINE_DIR / 'Components'}")
    if not KICKSTART_YAML.is_file():
        die(f"Missing {KICKSTART_YAML}")
    for m in models:
        cfg = MODELS[m]
        amiga = cfg["amigaos_dir"]
        if not (amiga / "ROMs").is_dir():
            die(f"Missing {amiga / 'ROMs'} (for {m})")
        if not (amiga / "ADFs").is_dir():
            die(f"Missing {amiga / 'ADFs'} (for {m})")
        tmpl = TEMPLATES_DIR / cfg["template"]
        if not tmpl.is_file():
            die(f"Missing template {tmpl} (for {m})")


def _need_rom(r: dict, allowed: tuple = VALID_ROMS) -> str:
    """Require the row to carry an explicit `rom:` field from `allowed`."""
    rom = r.get("rom")
    if rom is None:
        die(f"row {r!r} is missing required `rom:` field "
            f"(must be one of {', '.join(allowed)})")
    rom = rom.upper()
    if rom not in allowed:
        die(f"`rom:` must be one of {allowed} (got {r.get('rom')!r}) "
            f"in row {r!r}")
    return rom


def _ensure_unique_target(target: str, patched: dict) -> None:
    """Reject two rows that touch the same stock module."""
    if target in patched:
        die(f"Two rows target stock module '{target}' in {KICKSTART_YAML.name}")


def _link_adf(adf_path: Path, workdir: Path) -> Path:
    """Symlink an ADF into workdir so capcli's `loadadf "<basename>"` finds it."""
    if not adf_path.is_file():
        die(f"Missing ADF: {adf_path}")
    link = workdir / adf_path.name
    if not link.exists():
        link.symlink_to(adf_path)
    return link


def _handle_skip(r: dict, workdir: Path, by_rom: dict, patched: dict) -> None:
    """`skip:` drop a stock F8 module entirely (no `rom:` allowed)."""
    target = r["skip"]
    if "rom" in r:
        die(f"`skip` row must not specify `rom:`, skipped modules "
            f"aren't added to either ROM bank: {r!r}")
    _ensure_unique_target(target, patched)
    patched[target] = f"# Skipped: {target} (see kickstart.yaml)"


def _handle_relocate(r: dict, workdir: Path, by_rom: dict, patched: dict) -> None:
    """`relocate:` move a stock F8 module to E0 (keep stock content)."""
    target = r["relocate"]
    _need_rom(r, allowed=("E0",))
    _ensure_unique_target(target, patched)
    patched[target] = f"# Relocated to E0: {target} (stock from $SOURCEROM)"
    by_rom["E0"].append(SourceRomEntry(name=target))


def _handle_replace(r: dict, workdir: Path, by_rom: dict, patched: dict) -> None:
    """`replace:` + `with:` (file) or `adf:`+`adf_path:` (ADF entry).

    `rom: "F8"` substitutes at the stock module's natural slot; `rom: "E0"`
    suppresses the F8 line and lands the substitute in E0 instead.
    """
    target = r["replace"]
    _ensure_unique_target(target, patched)
    rom_dst = _need_rom(r)

    if "with" in r:
        staged_path = r["with"]
        if rom_dst == "F8":
            patched[target] = (f"# Patched: {target}\n"
                               f'add "{staged_path}"')
        else:
            patched[target] = (f"# Relocated to E0: {target} "
                               f"(substituted with {staged_path})")
            by_rom["E0"].append(FileEntry(name=Path(staged_path).name))
    elif "adf" in r:
        # `adf_path` is case-sensitive: capcli's `add ADF:/<path>` does an
        # exact-case lookup against the entry names in the loaded ADF.
        # A mismatch (e.g. `LIBS/RESOURCES/` vs the actual `LIBS/Resources/`)
        # leaves TEMPFILE.bin unwritten and capcli logs
        # `ERROR: Unable to open file TEMPFILE.bin` while still exiting 0.
        # `run_capcli` greps the log for `error:` and dies hard, so any
        # case typo surfaces as a build failure instead of silently shipping
        # a broken ROM.
        adf = _link_adf(Path(r["adf"]), workdir)
        inner = r["adf_path"]
        if rom_dst == "F8":
            patched[target] = (f"# Patched: {target} (from {adf.name})\n"
                               f'loadadf "{adf.name}"\n'
                               f"add ADF:/{inner}")
        else:
            patched[target] = (f"# Relocated to E0: {target} "
                               f"(substituted from {adf.name})")
            by_rom["E0"].append(AdfGroup(adf_ref=adf.name, libs=[inner]))
    else:
        die(f"`replace` row for '{target}' needs either `with:` (file path) "
            f"or `adf:`+`adf_path:` (entry inside an ADF)")


def _handle_adf(r: dict, workdir: Path, by_rom: dict, patched: dict) -> None:
    """`adf:` + `adf_path:` (specific ADF) or `adf_modules:` (model `$ADF`).

    Consecutive rows that share the same ADF reference collapse into a
    single `loadadf` followed by multiple `add ADF:/...` directives.
    """
    rom = _need_rom(r)
    if "adf_modules" in r:
        adf_ref, lib_path = "$ADF", r["adf_modules"]
    else:
        adf = _link_adf(Path(r["adf"]), workdir)
        adf_ref, lib_path = adf.name, r["adf_path"]
    bucket = by_rom[rom]
    if bucket and isinstance(bucket[-1], AdfGroup) and bucket[-1].adf_ref == adf_ref:
        bucket[-1].libs.append(lib_path)
    else:
        bucket.append(AdfGroup(adf_ref=adf_ref, libs=[lib_path]))


def _handle_file(r: dict, workdir: Path, by_rom: dict, patched: dict) -> None:
    """`file:` add a file from disk to a ROM bank by basename."""
    rom = _need_rom(r)
    src = Path(r["file"])
    if not src.is_absolute():
        src = REPO_ROOT / src
    if not src.is_file():
        die(f"Missing module: {src}")
    shutil.copy2(src, workdir / src.name)
    by_rom[rom].append(FileEntry(name=src.name))


# ---------------------------------------------------------------------------
# ROM resident scanner
# ---------------------------------------------------------------------------

_NT_NAMES: dict[int, str] = {
    1: "task",
    2: "int",
    3: "dev",
    4: "port",
    5: "msg",
    8: "res",
    9: "lib",
    10: "mem",
    11: "sint",
    14: "sem",
}

_ROM_F8_BASE = 0xF80000
_ROM_E0_BASE = 0xE00000
_ROM_HALF    = 0x80000   # 512 KB per bank


def _rom_offset_to_addr(offset: int) -> int:
    """Map a byte offset in the ROM binary -> Amiga ROM address."""
    if offset < _ROM_HALF:
        return _ROM_F8_BASE + offset
    return _ROM_E0_BASE + (offset - _ROM_HALF)


def _rom_addr_to_offset(addr: int) -> int | None:
    """Map an Amiga ROM address -> byte offset in the ROM binary; None if outside both banks."""
    if _ROM_F8_BASE <= addr < _ROM_F8_BASE + _ROM_HALF:
        return addr - _ROM_F8_BASE
    if _ROM_E0_BASE <= addr < _ROM_E0_BASE + _ROM_HALF:
        return (addr - _ROM_E0_BASE) + _ROM_HALF
    return None


def _read_cstring(data: bytes, off: int | None) -> str:
    """Return null-terminated Latin-1 string at *off* in *data*; '?' on failure.

    Control characters (newlines, tabs, etc.) are collapsed to a single space
    and leading/trailing whitespace is stripped.  AmigaOS IDStrings routinely
    embed a leading or trailing \\n which would otherwise break table rows.
    """
    if off is None or off < 0 or off >= len(data):
        return "?"
    end = data.find(b"\x00", off)
    if end == -1:
        end = off + 256
    try:
        s = data[off:end].decode("latin-1")
        s = " ".join(s.split())   # collapse all whitespace / control chars
        return s or "?"
    except Exception:
        return "?"


def scan_residents(rom_path: Path) -> list[dict]:
    """Scan a 1 MB Amiga Kickstart ROM binary for Resident structures.

    Scans every even offset for RTC_MATCHWORD (0x4AFC), then validates the
    self-pointer (rt_MatchTag must equal the ROM address of the match word).

    Address mapping for the combined 1 MB ROM binary:
      - File bytes 0x00000-0x7FFFF: F8 bank (Amiga 0xF80000-0xFFFFFF)
      - File bytes 0x80000-0xFFFFF: E0 bank (Amiga 0xE00000-0xE7FFFF)

    Returns a list of dicts (F8-first, E0-second, in discovery order) with
    keys: bank, rom_addr, rt_type, type_name, version, pri, name, idstring.
    """
    data = rom_path.read_bytes()
    n = len(data)
    results = []
    i = 0
    while i <= n - 26:
        if data[i] == 0x4A and data[i + 1] == 0xFC:
            rom_addr = _rom_offset_to_addr(i)
            tag_addr = struct.unpack_from(">I", data, i + 2)[0]
            if tag_addr == rom_addr:
                endskip_addr = struct.unpack_from(">I", data, i + 6)[0]
                rt_type  = data[i + 12]
                version  = data[i + 11]
                pri      = struct.unpack_from(">b", data, i + 13)[0]
                name_off = _rom_addr_to_offset(struct.unpack_from(">I", data, i + 14)[0])
                id_off   = _rom_addr_to_offset(struct.unpack_from(">I", data, i + 18)[0])
                bank     = "F8" if i < _ROM_HALF else "E0"
                results.append({
                    "bank":         bank,
                    "rom_addr":     rom_addr,
                    "endskip_addr": endskip_addr,
                    "rt_type":      rt_type,
                    "type_name":    _NT_NAMES.get(rt_type, f"t{rt_type}"),
                    "version":      version,
                    "pri":          pri,
                    "name":         _read_cstring(data, name_off),
                    "idstring":     _read_cstring(data, id_off),
                })
        i += 2
    return results


def _annotate_residents(residents: list[dict]) -> None:
    """Add a ``note`` key to each resident dict, derived purely from the scan.

    When the same resident name appears more than once (e.g. workbench.library
    in both F8 v40 and E0 v47), the lower-version copy will lose the
    ResidentMatcher race at boot.  Flag it so the user can spot it in the table.
    No build-config knowledge used.
    """
    by_name: dict[str, list[dict]] = defaultdict(list)
    for r in residents:
        r["note"] = ""
        by_name[r["name"]].append(r)

    for copies in by_name.values():
        if len(copies) > 1:
            max_ver = max(c["version"] for c in copies)
            winner  = next(c for c in copies if c["version"] == max_ver)
            for c in copies:
                if c["version"] < max_ver:
                    c["note"] = f"shadowed -> {winner['bank']} v{max_ver}"


def _print_residents(model: str, residents: list[dict], rom_name: str = "ROM") -> None:
    """Print a tabulated ROM resident report using tabulate.

    Binary audit: every Resident structure found in the ROM is listed.
    Same-name entries at lower rt_Version are annotated as shadowed (they lose
    the ResidentMatcher race at boot to the higher-version copy).
    """
    ID_COL = 50

    def trunc(s: str, n: int) -> str:
        return s if len(s) <= n else s[:n - 1] + "..."

    has_notes = any(r.get("note") for r in residents)
    headers = ["Bank", "Addr", "Type", "Ver", "Pri", "Name", "IDString"]
    if has_notes:
        headers.append("Notes")

    rows = []
    for r in residents:
        row: list = [
            r["bank"],
            f"{r['rom_addr']:06X}",
            r["type_name"],
            r["version"],
            r["pri"],
            r["name"],
            trunc(r["idstring"], ID_COL),
        ]
        if has_notes:
            row.append(r.get("note", ""))
        rows.append(row)

    n_shadowed = sum(1 for r in residents if r.get("note"))
    summary = f"{len(residents)} found"
    if n_shadowed:
        summary += f", {n_shadowed} shadowed by higher version"

    align = ("left", "left", "left", "right", "right", "left", "left")
    if has_notes:
        align = align + ("left",)

    print(f"\n  Residents in {rom_name}: {model} ({summary}):")
    for line in tabulate(rows, headers=headers, tablefmt="simple",
                         colalign=align).splitlines():
        print("  " + line)
    print()


# ---------------------------------------------------------------------------
# Module resolution
# ---------------------------------------------------------------------------

def resolve_extra_modules(
    workdir: Path, cpu: str, os_: str
) -> tuple[dict[str, list], dict[str, str]]:
    """Walk the `modules` list from kickstart.yaml; stage sources into workdir.

    Returns `(modules_by_rom, patched_modules)`:
    - `modules_by_rom`: dict keyed by ROM ("E0"/"F8") whose values are
      ordered lists of FileEntry / AdfGroup / SourceRomEntry to add to
      that ROM bank.
    - `patched_modules`: dict mapping a stock F8 module name to the
      capcli-script fragment that replaces its natural `add "$SOURCEROM"
      <name>` line.  Fragments are either a suppression comment
      (`skip` / `relocate` / `replace` rom: "E0"), a `# Patched:` +
      `add "<file>"` pair (`replace` + `with:`), or a `# Patched:` +
      `loadadf "<adf>"` + `add ADF:/<inner>` triplet (`replace` + `adf:`).

    See the argparse `--help` epilog and `docs/kickstart.md` for the
    full YAML schema.
    """
    by_rom: dict[str, list] = defaultdict(list)
    patched: dict[str, str] = {}

    for r in CONFIG["modules"]:
        if r.get("cpu") and r["cpu"] != cpu:
            continue
        if r.get("os") and r["os"] != os_:
            continue

        if "skip" in r:
            _handle_skip(r, workdir, by_rom, patched)
        elif "relocate" in r:
            _handle_relocate(r, workdir, by_rom, patched)
        elif "replace" in r:
            _handle_replace(r, workdir, by_rom, patched)
        elif "adf_modules" in r or "adf" in r:
            _handle_adf(r, workdir, by_rom, patched)
        elif "file" in r:
            _handle_file(r, workdir, by_rom, patched)
        else:
            die(f"row has no recognized verb (skip/relocate/replace/"
                f"adf_modules/adf/file): {r!r}")

    return dict(by_rom), patched


def render_template(
    workdir: Path,
    cfg: dict,
    model: str,
    modules_by_rom: dict[str, list],
    patched_modules: dict[str, str],
) -> Path:
    """Render the model's Jinja template -> workdir/capitoline.script."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
    )
    tmpl = env.get_template(cfg["template"])
    text = tmpl.render(
        model=model,
        os=cfg["os"],
        sourcerom_crc=cfg["sourcerom_crc"],
        adf_crc=cfg["adf_crc"],
        saveprofile=cfg["saveprofile"],
        outdir=".",
        f8_modules=modules_by_rom.get("F8", []),
        e0_modules=modules_by_rom.get("E0", []),
        patched_modules=patched_modules,
    )
    out = workdir / "capitoline.script"
    out.write_text(text)
    return out


def run_capcli(workdir: Path, script: Path) -> Path:
    """Run capcli.Linux from workdir with stdin from script. Returns log path."""
    log = workdir / "capitoline.log"
    with script.open("rb") as stdin, log.open("wb") as out:
        result = subprocess.run(
            [str(CAPCLI)],
            cwd=workdir,
            stdin=stdin,
            stdout=out,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if result.returncode != 0:
        _dump_log_tail(log)
        die(f"capcli.Linux failed - see {log}")
    # capcli exits 0 even when it silently drops `add` directives that
    # don't fit or can't be processed; surface those so the build doesn't
    # ship a broken ROM.
    log_text = log.read_text(errors="replace")
    log_lc = log_text.lower()
    if "space in rom" in log_lc:
        _dump_log_tail(log)
        die(f"capcli reported 'no space in rom' - module silently dropped. See {log}")
    # E.g. `ERROR: Unable to open file TEMPFILE.bin` after a `loadadf + add
    # ADF:/...` pair while building an F8 ROM (capcli mishandles ADF-source
    # adds in F8 mode and drops the component).
    if "error:" in log_lc:
        _dump_log_tail(log)
        die(f"capcli logged an ERROR - module(s) likely dropped silently. See {log}")
    return log


def _dump_log_tail(log: Path, n: int = 40) -> None:
    try:
        lines = log.read_text(errors="replace").splitlines()
        for line in lines[-n:]:
            print(line, file=sys.stderr)
    except OSError:
        pass


def build_one(model: str, verbose: bool = True, name: str = "cfd") -> None:
    cfg = MODELS[model]
    cpu = cfg["cpu"]
    os_ = cfg["os"]
    amiga = cfg["amigaos_dir"]

    print()
    print(_c(f"  Building {model} ROM  (OS {os_}, CPU {cpu})", _BOLD, _CYAN))

    workdir = SCRIPT_DIR / f"workdir_{model}"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    try:
        (workdir / "Components").symlink_to(CAPITOLINE_DIR / "Components")
        (workdir / "Capitoline Hashes").symlink_to(CAPITOLINE_DIR / "Capitoline Hashes")
        (workdir / "ROMs").symlink_to(amiga / "ROMs")
        (workdir / "ADFs").symlink_to(amiga / "ADFs")

        modules_by_rom, patched_modules = resolve_extra_modules(workdir, cpu, os_)
        script = render_template(workdir, cfg, model, modules_by_rom, patched_modules)
        log = run_capcli(workdir, script)

        f8 = workdir / "cfd.F8"
        e0 = workdir / "cfd.E0"
        if not f8.is_file():
            _dump_log_tail(log)
            die(f"Missing {f8}")
        if not e0.is_file():
            _dump_log_tail(log)
            die(f"Missing {e0}")

        model_out = OUT_DIR / model
        if model_out.exists():
            shutil.rmtree(model_out)
        model_out.mkdir(parents=True)

        rom = model_out / f"{name}.rom"
        with rom.open("wb") as out:
            out.write(f8.read_bytes())
            out.write(e0.read_bytes())

        shutil.copy2(e0, model_out / f"{name}.E0")
        shutil.copy2(f8, model_out / f"{name}.F8")
        shutil.copy2(log, model_out / "capitoline.log")
        shutil.copy2(script, model_out / "capitoline.script")

        bin_files: list[Path] = []
        for f in sorted(workdir.glob("cfd*.bin")):
            dest_name = name + f.name[len("cfd"):]
            dest = model_out / dest_name
            shutil.copy2(f, dest)
            bin_files.append(dest)

        f8_out = model_out / f"{name}.F8"
        e0_out = model_out / f"{name}.E0"

        all_files: list[tuple[Path, str]] = (
            [(rom, "")]
            + [(f8_out, "1/2"), (e0_out, "2/2")]
            + [(bf, f"{i}/{len(bin_files)}") for i, bf in enumerate(bin_files, 1)]
        )
        lw = max(len(p.name) for p, _ in all_files)

        rel = model_out.relative_to(REPO_ROOT)
        print(f"  Output: {_c(str(rel) + '/', _YELLOW)}")
        for path, tag in all_files:
            sz  = path.stat().st_size
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            fname = _c(path.name, _CYAN) + " " * (lw - len(path.name))
            tag_s = f"{tag:>3}" if tag else "   "
            print(f"    {fname}  {tag_s}  {sz:>12,} bytes  {sha}")
        if verbose:
            residents = scan_residents(rom)
            _annotate_residents(residents)
            _print_residents(model, residents, rom.name)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


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
      adf_crc         CRC of the modules ADF
      saveprofile     Capitoline saveprofile directive (empty string = none)
      template        Jinja2 template filename under templates/
      amigaos_dir     Path to the AmigaOS installation (must contain ROMs/ and ADFs/)

  modules:
    Ordered list of entries added on top of the stock ROM.  Each entry uses
    exactly one verb; `rom:` is mandatory on every verb except `skip:`.

    Verbs:
      {adf_modules: <inner-path>, rom: "E0"|"F8"}
          Add a single library from the model's own modules ADF.

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

    Row order = order of `add` directives emitted into the Capitoline script.

  Note: adf_path values are case-sensitive (Capitoline does an exact-case
  lookup inside the ADF).  A mismatch causes the build to fail hard.
"""


class _PrintAndExit(argparse.Action):
    """argparse action: print a text block and exit."""
    def __init__(self, option_strings, dest, text="", **kw):
        super().__init__(option_strings, dest, nargs=0, **kw)
        self._text = text

    def __call__(self, parser, namespace, values, option_string=None):
        print(self._text, end="")
        parser.exit()


def parse_args(argv: list[str]) -> tuple[list[str], bool, str]:
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
        "--list-targets",
        action=_PrintAndExit,
        text=_TARGETS_HELP,
        help="list available build targets and exit",
    )
    parser.add_argument(
        "--list-config",
        action=_PrintAndExit,
        text=_CONFIG_HELP,
        help="show kickstart.yaml schema reference and exit",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="all",
        help="which ROM(s) to build (default: all, every variant)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="suppress the resident table printed after each build",
    )
    parser.add_argument(
        "-n", "--name",
        default="cfd",
        metavar="NAME",
        help="basename for output files (default: cfd -> cfd.rom, cfd.F8, cfd.E0, ...)",
    )
    aliases = {
        "a600":            ["A600-3.2.3"],
        "a1200":           ["A1200-3.2.3"],
        "a600-3.2.3":      ["A600-3.2.3"],
        "a1200-3.2.3":     ["A1200-3.2.3"],
        "a600-3.1":        ["A600-3.1"],
        "a1200-3.1":       ["A1200-3.1"],
        "a600-2.05":       ["A600-2.05"],
        "a500plus":        ["A500plus-2.04"],
        "a500plus-2.04":   ["A500plus-2.04"],
        "2.04":            ["A500plus-2.04"],
        "2.05":            ["A600-2.05"],
        "2.0x":            ["A600-2.05", "A500plus-2.04"],
        "3.1":             ["A600-3.1",   "A1200-3.1"],
        "3.2":             ["A600-3.2.3", "A1200-3.2.3"],
        "3.2.3":           ["A600-3.2.3", "A1200-3.2.3"],
        "all":             ["A600-3.2.3", "A1200-3.2.3", "A600-3.1", "A1200-3.1", "A600-2.05", "A500plus-2.04"],
        "both":            ["A600-3.2.3", "A1200-3.2.3"],
        "":                ["A600-3.2.3", "A1200-3.2.3"],
    }
    args = parser.parse_args(argv)
    target = args.target.lower()
    if target not in aliases:
        parser.error(
            f"Unknown target '{args.target}'. Try: a600 | a1200 | "
            f"a600-3.2.3 | a1200-3.2.3 | a600-3.1 | a1200-3.1 | "
            f"a600-2.05 | a500plus-2.04 | 2.04 | 2.05 | 3.1 | 3.2.3 | all"
        )
    return aliases[target], not args.quiet, args.name


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    models, verbose, name = parse_args(argv)
    preflight(models)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for m in models:
        build_one(m, verbose=verbose, name=name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
