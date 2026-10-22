"""ROM resident scanner and audit-report printer."""

from __future__ import annotations

import shutil
import struct
import textwrap
from collections import defaultdict
from pathlib import Path

from .colour import _DIM, _ITALIC, _c

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
_ROM_HALF = 0x80000  # 512 KB per bank

# Resident structure layout (exec/resident.h). All multi-byte fields big-endian.
#
#   offset  size  field          notes
#   ------  ----  -------------  --------------------------------------------
#     0     2     rt_MatchWord   0x4AFC (RTC_MATCHWORD)
#     2     4     rt_MatchTag    self-pointer back to rt_MatchWord
#     6     4     rt_EndSkip     end-of-resident pointer (scanner skip)
#    10     1     rt_Flags       (unused here)
#    11     1     rt_Version
#    12     1     rt_Type        NT_LIBRARY / NT_DEVICE / ...
#    13     1     rt_Pri         signed
#    14     4     rt_Name        ROM-address pointer to library name
#    18     4     rt_IdString    ROM-address pointer to ID string
#    22     4     rt_Init        (unused here)
_RTC_MATCHWORD = 0x4AFC
_RT_OFF_MATCHTAG = 2
_RT_OFF_ENDSKIP = 6
_RT_OFF_VERSION = 11
_RT_OFF_TYPE = 12
_RT_OFF_PRI = 13
_RT_OFF_NAME = 14
_RT_OFF_IDSTRING = 18
_RT_STRUCT_MIN_BYTES = 26
_CSTR_FALLBACK_LEN = 256


def _rom_offset_to_addr(offset: int, e0_first: bool = False) -> int:
    """Map a byte offset in the ROM binary -> Amiga ROM address."""
    first, second = (_ROM_E0_BASE, _ROM_F8_BASE) if e0_first else (_ROM_F8_BASE, _ROM_E0_BASE)
    if offset < _ROM_HALF:
        return first + offset
    return second + (offset - _ROM_HALF)


def _rom_addr_to_offset(addr: int, e0_first: bool = False) -> int | None:
    """Map an Amiga ROM address -> byte offset in the ROM binary; None if outside both banks."""
    first, second = (_ROM_E0_BASE, _ROM_F8_BASE) if e0_first else (_ROM_F8_BASE, _ROM_E0_BASE)
    if first <= addr < first + _ROM_HALF:
        return addr - first
    if second <= addr < second + _ROM_HALF:
        return (addr - second) + _ROM_HALF
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
        end = off + _CSTR_FALLBACK_LEN
    try:
        s = data[off:end].decode("latin-1")
        s = " ".join(s.split())  # collapse all whitespace / control chars
        return s or "?"
    except Exception:
        return "?"


def scan_residents(rom_path: Path, e0_first: bool = False) -> list[dict]:
    """Scan a 1 MB Amiga Kickstart ROM binary for Resident structures.

    Scans every even offset for RTC_MATCHWORD (0x4AFC), then validates the
    self-pointer (rt_MatchTag must equal the ROM address of the match word).

    Address mapping for the combined 1 MB ROM binary (default order):
      - File bytes 0x00000-0x7FFFF: F8 bank (Amiga 0xF80000-0xFFFFFF)
      - File bytes 0x80000-0xFFFFF: E0 bank (Amiga 0xE00000-0xE7FFFF)
    With `e0_first` the two banks swap places in the file.

    Returns a list of dicts (in file order, discovery order within a bank) with
    keys: bank, rom_addr, rt_type, type_name, version, pri, name, idstring.
    """
    data = rom_path.read_bytes()
    n = len(data)
    results = []
    mw_hi = (_RTC_MATCHWORD >> 8) & 0xFF
    mw_lo = _RTC_MATCHWORD & 0xFF
    i = 0
    while i <= n - _RT_STRUCT_MIN_BYTES:
        if data[i] == mw_hi and data[i + 1] == mw_lo:
            rom_addr = _rom_offset_to_addr(i, e0_first)
            tag_addr = struct.unpack_from(">I", data, i + _RT_OFF_MATCHTAG)[0]
            if tag_addr == rom_addr:
                endskip_addr = struct.unpack_from(">I", data, i + _RT_OFF_ENDSKIP)[0]
                rt_type = data[i + _RT_OFF_TYPE]
                version = data[i + _RT_OFF_VERSION]
                pri = struct.unpack_from(">b", data, i + _RT_OFF_PRI)[0]
                name_off = _rom_addr_to_offset(
                    struct.unpack_from(">I", data, i + _RT_OFF_NAME)[0], e0_first
                )
                id_off = _rom_addr_to_offset(
                    struct.unpack_from(">I", data, i + _RT_OFF_IDSTRING)[0], e0_first
                )
                bank = (
                    ("E0" if e0_first else "F8") if i < _ROM_HALF else ("F8" if e0_first else "E0")
                )
                results.append(
                    {
                        "bank": bank,
                        "rom_addr": rom_addr,
                        "endskip_addr": endskip_addr,
                        "rt_type": rt_type,
                        "type_name": _NT_NAMES.get(rt_type, f"t{rt_type}"),
                        "version": version,
                        "pri": pri,
                        "name": _read_cstring(data, name_off),
                        "idstring": _read_cstring(data, id_off),
                    }
                )
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
            winner = next(c for c in copies if c["version"] == max_ver)
            for c in copies:
                if c["version"] < max_ver:
                    c["note"] = f"shadowed -> {winner['bank']} v{max_ver}"


# Report columns and their alignment ("<" left, ">" right).
_COLUMNS = {"Bank": "<", "Addr": "<", "Type": "<", "Ver": ">", "Pri": ">", "Name": "<"}


def _print_residents(model: str, residents: list[dict], rom_name: str = "ROM") -> None:
    """Print the ROM resident report.

    Binary audit: every Resident structure found in the ROM is listed.
    Same-name entries at lower rt_Version are annotated as shadowed (they lose
    the ResidentMatcher race at boot to the higher-version copy); the note is
    printed dim and italic under the IDString, which wraps instead of being cut.
    """
    rows = [
        {
            "Bank": r["bank"],
            "Addr": f"{r['rom_addr']:06X}",
            "Type": r["type_name"],
            "Ver": r["version"],
            "Pri": r["pri"],
            "Name": r["name"],
        }
        for r in residents
    ]
    width = {c: max(len(c), *(len(str(row[c])) for row in rows)) for c in _COLUMNS}

    def line(row: dict) -> str:
        return "  ".join(f"{row[c]:{align}{width[c]}}" for c, align in _COLUMNS.items())

    header = line({c: c for c in _COLUMNS})
    rule = line({c: "-" * width[c] for c in _COLUMNS})

    # IDString gets the terminal width left over by the other columns.
    id_at = 2 + len(header) + 2
    id_width = max(40, shutil.get_terminal_size((160, 24)).columns - id_at - 1)

    n_shadowed = sum(1 for r in residents if r.get("note"))
    summary = f"{len(residents)} found"
    if n_shadowed:
        summary += f", {n_shadowed} shadowed by higher version"

    print(f"\n  Residents in {rom_name}: {model} ({summary}):")
    print(f"  {header}  IDString")
    print(f"  {rule}  {'-' * id_width}")
    for row, r in zip(rows, residents, strict=True):
        first, *more = textwrap.wrap(r["idstring"], id_width) or [""]
        print(f"  {line(row)}  {first}")
        for rest in more:
            print(" " * id_at + rest)
        if r.get("note"):
            print(" " * id_at + _c(r["note"], _DIM, _ITALIC))
    print()
