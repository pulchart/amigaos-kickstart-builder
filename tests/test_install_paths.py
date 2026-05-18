"""OUT_DIR and workdir resolve against the user's CWD, not the install tree.

This is the property a packaged install relies on: when kickstart is at
/usr/share/amigaos-kickstart-builder/, builds must still land under the
user's CWD instead of writing into a read-only install dir.
"""

from __future__ import annotations

import os
from pathlib import Path

from kickstart.paths import OUT_DIR


def test_out_dir_is_relative():
    assert not OUT_DIR.is_absolute()


def test_out_dir_resolves_under_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resolved = (OUT_DIR / "profile" / "model").resolve()
    assert resolved.is_relative_to(tmp_path)


def test_workdir_resolves_under_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Mirrors the construction in build._prepare_workdir.
    workdir = Path.cwd() / "workdir_A600-3.2.3"
    assert workdir.is_relative_to(tmp_path)


def test_cli_list_configs_runs_from_any_cwd(tmp_path, monkeypatch, capsys):
    """--list-configs reads from the bundled config/ regardless of CWD."""
    monkeypatch.chdir(tmp_path)
    from kickstart.cli import main

    rc = main(["--list-configs"])
    captured = capsys.readouterr()
    assert rc == 0
    # Discovery still finds the source-tree configs even though CWD changed.
    assert {"bare", "cfd", "iconlib"} <= set(captured.out.split())
    # No spurious files in tmp_path.
    assert os.listdir(tmp_path) == []
