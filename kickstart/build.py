"""Build orchestration: workdir setup, module resolution, capcli invocation, output staging."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .colour import _BLUE, _BOLD, _CYAN, _GREEN, _RED, _YELLOW, _c
from .config import Cfg
from .errors import die
from .handlers import (
    _handle_adf,
    _handle_file,
    _handle_relocate,
    _handle_replace,
    _handle_skip,
)
from .paths import CAPCLI, CAPITOLINE_DIR, OUT_DIR, TEMPLATES_DIR
from .residents import _annotate_residents, _print_residents, scan_residents


def preflight(cfg: Cfg, models: list[str]) -> None:
    """Verify capcli, Components, the active config, and each model's ROM/ADF/template are present."""
    if not (CAPCLI.is_file() and os.access(CAPCLI, os.X_OK)):
        die(f"Missing {CAPCLI}")
    if not (CAPITOLINE_DIR / "Components").is_dir():
        die(f"Missing {CAPITOLINE_DIR / 'Components'}")
    if not cfg.yaml_path.is_file():
        die(f"Missing {cfg.yaml_path}")
    for m in models:
        mcfg = cfg.models[m]
        amiga = mcfg["amigaos_dir"]
        if not (amiga / "ROMs").is_dir():
            die(f"Missing {amiga / 'ROMs'} (for {m})")
        if not (amiga / "ADFs").is_dir():
            die(f"Missing {amiga / 'ADFs'} (for {m})")
        tmpl = TEMPLATES_DIR / mcfg["template"]
        if not tmpl.is_file():
            die(f"Missing template {tmpl} (for {m})")


_SELECTORS = ("os", "cpu")


def _specificity(r: dict) -> int:
    """How many selector keys a row pins; more selectors = more specific."""
    return sum(1 for k in _SELECTORS if r.get(k))


def _row_target(r: dict) -> tuple[str | None, bool]:
    """Return `(module_name, is_placement)` for a row.

    Placement rows (file/adf/replace/relocate) emit an `add` for a module and
    therefore compete for most-specific-wins; `skip` only suppresses a stock
    slot, so it never competes and always applies.
    """
    if "skip" in r:
        return r["skip"], False
    if "relocate" in r:
        return r["relocate"], True
    if "replace" in r:
        return r["replace"], True
    if "adf" in r:
        return Path(r.get("adf_path", "")).name or None, True
    if "file" in r:
        return Path(r.get("file", "")).name or None, True
    return None, False


def resolve_extra_modules(
    cfg: Cfg, workdir: Path, cpu: str, os_: str
) -> tuple[dict[str, list], dict[str, str]]:
    """Walk the `modules` list from the active config; stage sources into workdir.

    Returns `(modules_by_rom, patched_modules)`:
    - `modules_by_rom`: dict keyed by ROM ("E0"/"F8") whose values are
      ordered lists of FileEntry / AdfGroup / SourceRomEntry to add to
      that ROM bank.
    - `patched_modules`: dict mapping a stock F8 module name to the
      capcli-script fragment that replaces its natural `add "$SOURCEROM"
      <name>` line.

    When several placement rows resolve to the same module name, the most
    specific match wins: a row pinning both `os:` and `cpu:` beats one pinning
    only `cpu:`, which beats an unscoped row.  This lets a module be placed in
    a different ROM bank per OS/CPU from one terse set of rows.  `skip` rows do
    not compete and always apply.
    """
    by_rom: dict[str, list] = defaultdict(list)
    patched: dict[str, str] = {}
    name = cfg.yaml_path.name

    # Rows passing the cpu/os filter, in original order (order matters for ADF
    # collapsing and F8 module sequencing).
    matching = [
        r
        for r in cfg.config["modules"]
        if not (r.get("cpu") and r["cpu"] != cpu) and not (r.get("os") and r["os"] != os_)
    ]

    # Most-specific-wins: per placement target, drop rows below the top tier.
    max_spec: dict[str, int] = {}
    for r in matching:
        target, is_placement = _row_target(r)
        if is_placement and target is not None:
            max_spec[target] = max(max_spec.get(target, -1), _specificity(r))

    for r in matching:
        target, is_placement = _row_target(r)
        if is_placement and target is not None and _specificity(r) < max_spec[target]:
            continue

        if "skip" in r:
            _handle_skip(r, workdir, by_rom, patched, name)
        elif "relocate" in r:
            _handle_relocate(r, workdir, by_rom, patched, name)
        elif "replace" in r:
            _handle_replace(r, workdir, by_rom, patched, name)
        elif "adf" in r:
            _handle_adf(r, workdir, by_rom, patched, name)
        elif "file" in r:
            _handle_file(r, workdir, by_rom, patched, name)
        else:
            die(f"row has no recognized verb (skip/relocate/replace/adf/file): {r!r}")

    return dict(by_rom), patched


def render_template(
    workdir: Path,
    model_cfg: dict,
    model: str,
    modules_by_rom: dict[str, list],
    patched_modules: dict[str, str],
) -> Path:
    """Render the model's Jinja template -> workdir/capitoline.script."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
    )
    tmpl = env.get_template(model_cfg["template"])
    text = tmpl.render(
        model=model,
        os=model_cfg["os"],
        sourcerom_crc=model_cfg["sourcerom_crc"],
        saveprofile=model_cfg["saveprofile"],
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
        die(f"capcli.Linux failed - see {workdir}")
    # capcli exits 0 even when it silently drops `add` directives that
    # don't fit or can't be processed; surface those so the build doesn't
    # ship a broken ROM.
    log_text = log.read_text(errors="replace")
    log_lc = log_text.lower()
    if "space in rom" in log_lc:
        _dump_log_tail(log)
        die(f"capcli reported 'no space in rom' - module silently dropped. See {workdir}")
    if "error:" in log_lc:
        _dump_log_tail(log)
        die(f"capcli logged an ERROR - module(s) likely dropped silently. See {workdir}")
    return log


def _dump_log_tail(log: Path, n: int = 40) -> None:
    """Print the last *n* meaningful (prompt-stripped) lines from a capcli log, colourised."""
    try:
        raw = log.read_text(errors="replace").splitlines()
    except OSError:
        return
    meaningful = []
    for line in raw:
        msg = line
        while msg.startswith("CapCLI>"):
            msg = msg[len("CapCLI>") :].lstrip()
        msg = msg.strip()
        if msg:
            meaningful.append(msg)
    if not meaningful:
        return
    print(f"{_c('--- Capitoline log (filtered) ---', _BOLD)}", file=sys.stderr)
    for msg in meaningful[-n:]:
        lc = msg.lower()
        if "error" in lc or "not enough space" in lc or "no space" in lc:
            print(_c(msg, _RED), file=sys.stderr)
        elif "unable" in lc or "warning" in lc:
            print(_c(msg, _YELLOW), file=sys.stderr)
        else:
            print(msg, file=sys.stderr)
    print(f"{_c('---------------------------------', _BOLD)}", file=sys.stderr)


def _bank_free(data: bytes) -> int:
    """Return the size of the largest contiguous 0xFF run.

    Capitoline fills unused ROM space with 0xFF.  The free region is a single
    contiguous block between the last module and the ROM footer; the footer
    itself is not 0xFF (it holds the checksum etc.), so rstrip gives 0.
    """
    return max((m.end() - m.start() for m in re.finditer(rb"\xff+", data)), default=0)


@dataclass
class _BuildArtefacts:
    workdir: Path
    script: Path
    log: Path
    f8: Path
    e0: Path


def _prepare_workdir(model: str, model_cfg: dict) -> Path:
    """Create a fresh workdir for *model* and symlink Capitoline/AmigaOS sources into it."""
    workdir = Path.cwd() / f"workdir_{model}"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    amiga = model_cfg["amigaos_dir"]
    (workdir / "Components").symlink_to(CAPITOLINE_DIR / "Components")
    (workdir / "Capitoline Hashes").symlink_to(CAPITOLINE_DIR / "Capitoline Hashes")
    (workdir / "ROMs").symlink_to(amiga / "ROMs")
    (workdir / "ADFs").symlink_to(amiga / "ADFs")
    return workdir


def _build_in_workdir(cfg: Cfg, model: str, model_cfg: dict, workdir: Path) -> _BuildArtefacts:
    """Resolve modules, render the capcli script, run capcli; return the produced artefacts."""
    modules_by_rom, patched_modules = resolve_extra_modules(
        cfg, workdir, model_cfg["cpu"], model_cfg["os"]
    )
    script = render_template(workdir, model_cfg, model, modules_by_rom, patched_modules)
    log = run_capcli(workdir, script)
    f8 = workdir / "cfd.F8"
    e0 = workdir / "cfd.E0"
    if not f8.is_file():
        _dump_log_tail(log)
        die(f"Missing {f8}")
    if not e0.is_file():
        _dump_log_tail(log)
        die(f"Missing {e0}")
    return _BuildArtefacts(workdir=workdir, script=script, log=log, f8=f8, e0=e0)


def _finalise_output(artefacts: _BuildArtefacts, model: str, name: str, verbose: bool) -> None:
    """Stage workdir outputs into out/<name>/<model>/, print the SHA + free-space report, audit residents."""
    workdir = artefacts.workdir
    model_out = (OUT_DIR / name / model).resolve()
    if model_out.exists():
        shutil.rmtree(model_out)
    model_out.mkdir(parents=True)

    rom = model_out / f"{name}.rom"
    with rom.open("wb") as out:
        out.write(artefacts.f8.read_bytes())
        out.write(artefacts.e0.read_bytes())

    shutil.copy2(artefacts.e0, model_out / f"{name}.E0")
    shutil.copy2(artefacts.f8, model_out / f"{name}.F8")
    shutil.copy2(artefacts.log, model_out / "capitoline.log")
    shutil.copy2(artefacts.script, model_out / "capitoline.script")

    bin_files: list[Path] = []
    for f in sorted(workdir.glob("cfd*.bin")):
        dest_name = name + f.name[len("cfd") :]
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

    file_rows: list[tuple[Path, str, int, str, int | None]] = []
    for path, tag in all_files:
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        free = _bank_free(data) if path.suffix in (".F8", ".E0") else None
        file_rows.append((path, tag, len(data), sha, free))

    free_vals = [fr for *_, fr in file_rows if fr is not None]
    fw = max(len(f"{v:,}") for v in free_vals) if free_vals else 0

    rel = model_out.relative_to(Path.cwd()) if model_out.is_relative_to(Path.cwd()) else model_out
    print(f"  Output: {_c(str(rel) + '/', _YELLOW)}")
    for path, tag, sz, sha, free in file_rows:
        fname = _c(path.name, _CYAN) + " " * (lw - len(path.name))
        tag_s = f"{tag:>3}" if tag else "   "
        if free is not None:
            pct = free / sz * 100
            fc = _GREEN if pct > 50 else _BLUE if pct > 20 else _YELLOW if pct > 10 else _RED
            free_s = _c(f"{free:{fw},} B free", fc)
        else:
            free_s = " " * (fw + 7)
        print(f"    {fname}  {tag_s}  {sz:>12,} bytes  {free_s}  {sha}")
    if verbose:
        residents = scan_residents(rom)
        _annotate_residents(residents)
        _print_residents(model, residents, rom.name)


def build_one(cfg: Cfg, model: str, verbose: bool = True, name: str = "cfd") -> None:
    """Build one ROM for *model* using *cfg*. Output lands in ``out/<name>/<model>/``."""
    model_cfg = cfg.models[model]
    cpu = model_cfg["cpu"]
    os_ = model_cfg["os"]

    print()
    print(
        _c("  Building ", _BOLD, _CYAN)
        + _c(name, _BOLD, _YELLOW)
        + _c(" / ", _BOLD, _CYAN)
        + _c(model, _BOLD, _CYAN)
        + _c(f" ROM  (OS {os_}, CPU {cpu})", _BOLD, _CYAN)
    )

    workdir = _prepare_workdir(model, model_cfg)
    try:
        artefacts = _build_in_workdir(cfg, model, model_cfg, workdir)
        _finalise_output(artefacts, model, name, verbose)
    except BaseException:
        # Keep the workdir on failure so the capcli log/script referenced in
        # the error message survive for inspection (a fresh build of this
        # model rmtrees the stale workdir in _prepare_workdir first).
        print(
            _c(f"  Workdir kept for inspection: {workdir}", _YELLOW),
            file=sys.stderr,
        )
        raise
    else:
        shutil.rmtree(workdir, ignore_errors=True)
