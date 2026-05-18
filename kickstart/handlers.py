"""Per-verb module-resolution handlers (skip/relocate/replace/adf/file)."""

from __future__ import annotations

import shutil
from pathlib import Path

from .config import AdfGroup, FileEntry, SourceRomEntry
from .errors import die
from .paths import VALID_ROMS


def _need_rom(r: dict, allowed: tuple = VALID_ROMS) -> str:
    """Require the row to carry an explicit `rom:` field from `allowed`."""
    rom = r.get("rom")
    if rom is None:
        die(f"row {r!r} is missing required `rom:` field (must be one of {', '.join(allowed)})")
    rom = rom.upper()
    if rom not in allowed:
        die(f"`rom:` must be one of {allowed} (got {r.get('rom')!r}) in row {r!r}")
    return rom


def _ensure_unique_target(target: str, patched: dict, config_name: str) -> None:
    """Reject two rows that touch the same stock module."""
    if target in patched:
        die(f"Two rows target stock module '{target}' in {config_name}")


def _link_adf(adf_path: Path, workdir: Path) -> Path:
    """Symlink an ADF into workdir so capcli's `loadadf "<basename>"` finds it."""
    if not adf_path.is_file():
        die(f"Missing ADF: {adf_path}")
    link = workdir / adf_path.name
    if not link.exists():
        link.symlink_to(adf_path)
    return link


def _handle_skip(r: dict, workdir: Path, by_rom: dict, patched: dict, config_name: str) -> None:
    """`skip:` drop a stock F8 module entirely (no `rom:` allowed)."""
    target = r["skip"]
    if "rom" in r:
        die(
            f"`skip` row must not specify `rom:`, skipped modules "
            f"aren't added to either ROM bank: {r!r}"
        )
    _ensure_unique_target(target, patched, config_name)
    patched[target] = f"# Skipped: {target} (see kickstart.yaml)"


def _handle_relocate(r: dict, workdir: Path, by_rom: dict, patched: dict, config_name: str) -> None:
    """`relocate:` move a stock F8 module to E0 (keep stock content)."""
    target = r["relocate"]
    _need_rom(r, allowed=("E0",))
    _ensure_unique_target(target, patched, config_name)
    patched[target] = f"# Relocated to E0: {target} (stock from $SOURCEROM)"
    by_rom["E0"].append(SourceRomEntry(name=target))


def _handle_replace(r: dict, workdir: Path, by_rom: dict, patched: dict, config_name: str) -> None:
    """`replace:` + `with:` (file) or `adf:`+`adf_path:` (ADF entry).

    `rom: "F8"` substitutes at the stock module's natural slot; `rom: "E0"`
    suppresses the F8 line and lands the substitute in E0 instead.
    """
    target = r["replace"]
    _ensure_unique_target(target, patched, config_name)
    rom_dst = _need_rom(r)

    if "with" in r:
        staged_path = r["with"]
        if rom_dst == "F8":
            patched[target] = f'# Patched: {target}\nadd "{staged_path}"'
        else:
            patched[target] = f"# Relocated to E0: {target} (substituted with {staged_path})"
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
            patched[target] = (
                f'# Patched: {target} (from {adf.name})\nloadadf "{adf.name}"\nadd ADF:/{inner}'
            )
        else:
            patched[target] = f"# Relocated to E0: {target} (substituted from {adf.name})"
            by_rom["E0"].append(AdfGroup(adf_ref=adf.name, libs=[inner]))
    else:
        die(
            f"`replace` row for '{target}' needs either `with:` (file path) "
            f"or `adf:`+`adf_path:` (entry inside an ADF)"
        )


def _handle_adf(r: dict, workdir: Path, by_rom: dict, patched: dict, config_name: str) -> None:
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


def _handle_file(r: dict, workdir: Path, by_rom: dict, patched: dict, config_name: str) -> None:
    """`file:` add a file from disk to a ROM bank by basename."""
    rom = _need_rom(r)
    src = Path(r["file"])
    if not src.is_absolute():
        src = Path.cwd() / src
    if not src.is_file():
        die(f"Missing module: {src}")
    shutil.copy2(src, workdir / src.name)
    by_rom[rom].append(FileEntry(name=src.name))
