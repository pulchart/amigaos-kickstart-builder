"""Per-verb handler tests: every verb generates the right capcli-script fragment.

These cover the fundamental risk that a bug in any handler would silently
produce a wrong ROM. The handlers' small internal helpers (_need_rom,
_ensure_unique_target, _link_adf) are exercised transitively.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest

from kickstart.config import AdfGroup, FileEntry, SourceRomEntry
from kickstart.handlers import (
    _handle_adf,
    _handle_file,
    _handle_relocate,
    _handle_replace,
    _handle_skip,
)


def _fresh():
    return defaultdict(list), {}


# --- skip --------------------------------------------------------------------


def test_handle_skip_records_suppression_fragment():
    by_rom, patched = _fresh()
    _handle_skip({"skip": "narrator.device"}, Path("/tmp"), by_rom, patched, "t.yaml")
    assert patched["narrator.device"].startswith("# Skipped:")
    assert not by_rom


def test_handle_skip_rejects_rom_field():
    by_rom, patched = _fresh()
    with pytest.raises(SystemExit):
        _handle_skip({"skip": "x", "rom": "F8"}, Path("/tmp"), by_rom, patched, "t.yaml")


# --- relocate ---------------------------------------------------------------


def test_handle_relocate_appends_source_rom_entry_to_e0():
    by_rom, patched = _fresh()
    _handle_relocate(
        {"relocate": "ramdrive.device", "rom": "E0"},
        Path("/tmp"), by_rom, patched, "t.yaml",
    )
    assert patched["ramdrive.device"].startswith("# Relocated to E0:")
    assert isinstance(by_rom["E0"][0], SourceRomEntry)
    assert by_rom["E0"][0].name == "ramdrive.device"


def test_handle_relocate_rejects_f8_target():
    by_rom, patched = _fresh()
    with pytest.raises(SystemExit):
        _handle_relocate(
            {"relocate": "x", "rom": "F8"}, Path("/tmp"), by_rom, patched, "t.yaml"
        )


# --- replace ----------------------------------------------------------------


def test_handle_replace_with_file_to_f8_emits_add_directive():
    by_rom, patched = _fresh()
    _handle_replace(
        {"replace": "exec.library", "with": "patched/exec.bin", "rom": "F8"},
        Path("/tmp"), by_rom, patched, "t.yaml",
    )
    assert patched["exec.library"].startswith("# Patched: exec.library")
    assert 'add "patched/exec.bin"' in patched["exec.library"]
    assert not by_rom["E0"]


def test_handle_replace_with_file_to_e0_relocates():
    by_rom, patched = _fresh()
    _handle_replace(
        {"replace": "exec.library", "with": "x/y.bin", "rom": "E0"},
        Path("/tmp"), by_rom, patched, "t.yaml",
    )
    assert patched["exec.library"].startswith("# Relocated to E0:")
    assert isinstance(by_rom["E0"][0], FileEntry)
    assert by_rom["E0"][0].name == "y.bin"  # basename only


def test_handle_replace_with_adf_to_f8_emits_loadadf_then_add(tmp_path):
    adf = tmp_path / "modules.adf"
    adf.write_bytes(b"")
    workdir = tmp_path / "wd"
    workdir.mkdir()
    by_rom, patched = _fresh()
    _handle_replace(
        {
            "replace": "card.resource",
            "adf": str(adf),
            "adf_path": "LIBS/Resources/card.resource",
            "rom": "F8",
        },
        workdir, by_rom, patched, "t.yaml",
    )
    frag = patched["card.resource"]
    assert f'loadadf "{adf.name}"' in frag
    assert "add ADF:/LIBS/Resources/card.resource" in frag


def test_handle_replace_with_adf_to_e0_appends_adf_group(tmp_path):
    adf = tmp_path / "modules.adf"
    adf.write_bytes(b"")
    workdir = tmp_path / "wd"
    workdir.mkdir()
    by_rom, patched = _fresh()
    _handle_replace(
        {"replace": "x", "adf": str(adf), "adf_path": "L/p", "rom": "E0"},
        workdir, by_rom, patched, "t.yaml",
    )
    grp = by_rom["E0"][0]
    assert isinstance(grp, AdfGroup)
    assert grp.adf_ref == adf.name
    assert grp.libs == ["L/p"]


def test_handle_replace_without_with_or_adf_dies():
    by_rom, patched = _fresh()
    with pytest.raises(SystemExit):
        _handle_replace(
            {"replace": "x", "rom": "F8"}, Path("/tmp"), by_rom, patched, "t.yaml"
        )


def test_handle_replace_rejects_duplicate_target():
    by_rom, patched = _fresh()
    patched["exec.library"] = "# already"
    with pytest.raises(SystemExit):
        _handle_replace(
            {"replace": "exec.library", "with": "x.bin", "rom": "F8"},
            Path("/tmp"), by_rom, patched, "t.yaml",
        )


# --- adf / adf_modules ------------------------------------------------------


def test_handle_adf_collapses_consecutive_same_adf(tmp_path):
    """Two rows pointing at the same ADF merge into one loadadf with multiple add directives."""
    adf = tmp_path / "mod.adf"
    adf.write_bytes(b"")
    workdir = tmp_path / "wd"
    workdir.mkdir()
    by_rom, patched = _fresh()
    _handle_adf(
        {"adf": str(adf), "adf_path": "L/fat95", "rom": "E0"},
        workdir, by_rom, patched, "t.yaml",
    )
    _handle_adf(
        {"adf": str(adf), "adf_path": "L/pfs3aio", "rom": "E0"},
        workdir, by_rom, patched, "t.yaml",
    )
    assert len(by_rom["E0"]) == 1
    assert by_rom["E0"][0].libs == ["L/fat95", "L/pfs3aio"]


def test_handle_adf_starts_new_group_when_adf_ref_changes(tmp_path):
    adf1 = tmp_path / "one.adf"
    adf1.write_bytes(b"")
    adf2 = tmp_path / "two.adf"
    adf2.write_bytes(b"")
    workdir = tmp_path / "wd"
    workdir.mkdir()
    by_rom, patched = _fresh()
    _handle_adf(
        {"adf": str(adf1), "adf_path": "a", "rom": "E0"},
        workdir, by_rom, patched, "t.yaml",
    )
    _handle_adf(
        {"adf": str(adf2), "adf_path": "b", "rom": "E0"},
        workdir, by_rom, patched, "t.yaml",
    )
    assert len(by_rom["E0"]) == 2


def test_handle_adf_modules_uses_dollar_adf_alias(tmp_path):
    workdir = tmp_path / "wd"
    workdir.mkdir()
    by_rom, patched = _fresh()
    _handle_adf(
        {"adf_modules": "L/fat95", "rom": "E0"},
        workdir, by_rom, patched, "t.yaml",
    )
    assert by_rom["E0"][0].adf_ref == "$ADF"


# --- file -------------------------------------------------------------------


def test_handle_file_copies_into_workdir_and_records_entry(tmp_path):
    src = tmp_path / "mod.bin"
    src.write_bytes(b"payload")
    workdir = tmp_path / "wd"
    workdir.mkdir()
    by_rom, patched = _fresh()
    _handle_file(
        {"file": str(src), "rom": "E0"},
        workdir, by_rom, patched, "t.yaml",
    )
    assert (workdir / "mod.bin").read_bytes() == b"payload"
    assert by_rom["E0"][0].name == "mod.bin"
