"""main(): -a reaches build_one and adds the CPU to the output name."""

from __future__ import annotations

import pytest
import yaml

from kickstart import cli

_MODEL = {
    "os": "3.2.3",
    "cpu": "68020",
    "sourcerom_crc": "0xDEADBEEF",
    "saveprofile": "",
    "template": "stub.j2",
    "amigaos_dir": "/opt/x",
}


@pytest.fixture
def calls(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(cli, "preflight", lambda cfg, models: None)
    monkeypatch.setattr(cli, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(
        cli, "build_one", lambda cfg, m, verbose, name, accel: seen.append((name, accel))
    )
    return seen


def _config(tmp_path, **extra):
    path = tmp_path / "prof.yaml"
    path.write_text(yaml.safe_dump({"models": {"A1200-3.2.3": _MODEL}, "modules": [], **extra}))
    return str(path)


def test_cli_accelerator_names_output(calls, tmp_path):
    cli.main(["-q", "-a", "68060", "-c", _config(tmp_path), "a1200-3.2.3"])
    assert calls == [("prof.68060", "68060")]


def test_no_accelerator_by_default(calls, tmp_path):
    cli.main(["-q", "-c", _config(tmp_path), "a1200-3.2.3"])
    assert calls == [("prof", None)]
