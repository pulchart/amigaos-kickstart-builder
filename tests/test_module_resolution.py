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
