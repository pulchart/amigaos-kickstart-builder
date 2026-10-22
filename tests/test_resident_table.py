"""Resident report: the shadowed note goes on its own line under the IDString."""

from __future__ import annotations

from kickstart.residents import _annotate_residents, _print_residents


def _res(bank, addr, version, name, idstring):
    return {
        "bank": bank,
        "rom_addr": addr,
        "type_name": "lib",
        "version": version,
        "pri": 0,
        "name": name,
        "idstring": idstring,
    }


def test_note_is_printed_under_the_idstring(capsys):
    residents = [
        _res("F8", 0xF80000, 40, "foo.library", "foo 40.1"),
        _res("E0", 0xE00000, 47, "foo.library", "foo 47.2"),
    ]
    _annotate_residents(residents)
    _print_residents("A1200", residents)
    lines = capsys.readouterr().out.splitlines()
    header = next(line for line in lines if "IDString" in line)
    row = lines.index(next(line for line in lines if "foo 40.1" in line))
    assert "Notes" not in header
    assert lines[row + 1].strip() == "shadowed -> E0 v47"
    assert len(lines[row + 1]) - len(lines[row + 1].lstrip()) == header.index("IDString")


def test_long_idstring_wraps_instead_of_being_cut(capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "100")
    idstring = " ".join(["word"] * 40)
    _print_residents("A1200", [_res("E0", 0xE00000, 1, "a", idstring)])
    lines = capsys.readouterr().out.splitlines()
    start = next(i for i, line in enumerate(lines) if line.lstrip().startswith("E0 "))
    text = " ".join(line.strip().split("  ")[-1] for line in lines[start : start + 4])
    assert text.count("word") == 40


def test_report_fits_the_terminal_width(capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "120")
    _print_residents("A1200", [_res("E0", 0xE00000, 1, "a", "z" * 300)])
    assert max(len(line) for line in capsys.readouterr().out.splitlines()) <= 120
