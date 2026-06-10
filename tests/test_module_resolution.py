"""resolve_extra_modules: verb dispatch + cpu/os filter."""

from __future__ import annotations

from pathlib import Path

import pytest

from kickstart.build import resolve_extra_modules
from kickstart.config import Cfg


def _cfg(tmp_path: Path, modules: list[dict]) -> Cfg:
    """Construct a minimal Cfg with the given `modules` list."""
    return Cfg(
        yaml_path=tmp_path / "t.yaml",
        config={"modules": modules},
        models={},
    )


def test_cpu_filter_skips_non_matching_rows(tmp_path):
    cfg = _cfg(
        tmp_path,
        [
            {"skip": "for_68000", "cpu": "68000"},
            {"skip": "for_68020", "cpu": "68020"},
            {"skip": "for_all"},
        ],
    )
    workdir = tmp_path / "wd"
    workdir.mkdir()
    _, patched = resolve_extra_modules(cfg, workdir, cpu="68000", os_="3.2.3")
    assert set(patched) == {"for_68000", "for_all"}


def test_os_filter_skips_non_matching_rows(tmp_path):
    cfg = _cfg(
        tmp_path,
        [
            {"skip": "only_3_2_3", "os": "3.2.3"},
            {"skip": "only_3_1", "os": "3.1"},
        ],
    )
    workdir = tmp_path / "wd"
    workdir.mkdir()
    _, patched = resolve_extra_modules(cfg, workdir, cpu="68000", os_="3.2.3")
    assert set(patched) == {"only_3_2_3"}


def test_dispatch_picks_handler_per_verb(tmp_path):
    src = tmp_path / "mod.bin"
    src.write_bytes(b"x")
    cfg = _cfg(
        tmp_path,
        [
            {"skip": "s"},
            {"relocate": "r", "rom": "E0"},
            {"replace": "p", "with": "p.bin", "rom": "F8"},
            {"file": str(src), "rom": "E0"},
        ],
    )
    workdir = tmp_path / "wd"
    workdir.mkdir()
    by_rom, patched = resolve_extra_modules(cfg, workdir, cpu="68000", os_="3.2.3")
    assert set(patched) == {"s", "r", "p"}
    # Only `relocate` and `file` land in E0; `replace` to F8 stays patched-only.
    assert len(by_rom["E0"]) == 2


def test_unknown_verb_dies(tmp_path):
    cfg = _cfg(tmp_path, [{"banana": "split"}])
    workdir = tmp_path / "wd"
    workdir.mkdir()
    with pytest.raises(SystemExit):
        resolve_extra_modules(cfg, workdir, cpu="68000", os_="3.2.3")


def _names(entries: list) -> list[str]:
    """FileEntry basenames in a ROM bank (ignores other entry kinds)."""
    return [e.name for e in entries if getattr(e, "name", None)]


def _icon_cfg(tmp_path: Path) -> Cfg:
    """skip + cpu-only F8 + os+cpu E0 rows, the canonical 'E0 on 3.2.3 else F8' shape."""
    f8_icon = tmp_path / "icon.library"
    f8_icon.write_bytes(b"f8")
    e0_dir = tmp_path / "e0"
    e0_dir.mkdir()
    e0_icon = e0_dir / "icon.library"
    e0_icon.write_bytes(b"e0")
    return _cfg(
        tmp_path,
        [
            {"skip": "icon.library"},
            {"file": str(f8_icon), "cpu": "68020", "rom": "F8"},
            {"file": str(e0_icon), "os": "3.2.3", "cpu": "68020", "rom": "E0"},
        ],
    )


def test_most_specific_wins_places_in_e0_on_3_2_3(tmp_path):
    workdir = tmp_path / "wd"
    workdir.mkdir()
    by_rom, patched = resolve_extra_modules(_icon_cfg(tmp_path), workdir, cpu="68020", os_="3.2.3")
    assert "icon.library" in patched  # skip always applies (no-op on 3.2.3)
    assert _names(by_rom.get("E0", [])) == ["icon.library"]
    assert _names(by_rom.get("F8", [])) == []  # less-specific F8 row dropped


def test_most_specific_wins_falls_back_to_f8_on_3_1(tmp_path):
    workdir = tmp_path / "wd"
    workdir.mkdir()
    by_rom, patched = resolve_extra_modules(_icon_cfg(tmp_path), workdir, cpu="68020", os_="3.1")
    assert "icon.library" in patched  # skip removes stock icon from F8
    assert _names(by_rom.get("F8", [])) == ["icon.library"]
    assert _names(by_rom.get("E0", [])) == []  # E0 row is 3.2.3-only, filtered out


def test_most_specific_wins_resolves_replace_conflict(tmp_path):
    f8 = tmp_path / "f8.bin"
    f8.write_bytes(b"f8")
    e0 = tmp_path / "e0.bin"
    e0.write_bytes(b"e0")
    cfg = _cfg(
        tmp_path,
        [
            {"replace": "icon.library", "with": str(f8), "cpu": "68020", "rom": "F8"},
            {
                "replace": "icon.library",
                "with": str(e0),
                "os": "3.2.3",
                "cpu": "68020",
                "rom": "E0",
            },
        ],
    )
    workdir = tmp_path / "wd"
    workdir.mkdir()
    # Without precedence both rows target 'icon.library' and trip
    # _ensure_unique_target; precedence keeps only the os+cpu E0 row.
    by_rom, patched = resolve_extra_modules(cfg, workdir, cpu="68020", os_="3.2.3")
    assert "icon.library" in patched
    assert _names(by_rom.get("E0", [])) == ["e0.bin"]
    assert "F8" not in by_rom


def test_same_specificity_tie_keeps_all_rows(tmp_path):
    icon_a = tmp_path / "a"
    icon_a.mkdir()
    (icon_a / "icon.library").write_bytes(b"a")
    icon_b = tmp_path / "b"
    icon_b.mkdir()
    (icon_b / "icon.library").write_bytes(b"b")
    cfg = _cfg(
        tmp_path,
        [
            {"file": str(icon_a / "icon.library"), "cpu": "68020", "rom": "E0"},
            {"file": str(icon_b / "icon.library"), "os": "3.2.3", "rom": "F8"},
        ],
    )
    workdir = tmp_path / "wd"
    workdir.mkdir()
    by_rom, _ = resolve_extra_modules(cfg, workdir, cpu="68020", os_="3.2.3")
    # Both rows are specificity 1 and both match -> neither dominates.
    assert _names(by_rom.get("E0", [])) == ["icon.library"]
    assert _names(by_rom.get("F8", [])) == ["icon.library"]
