"""_load_config: the models_from indirection is the non-trivial path worth covering."""

from __future__ import annotations

import pytest
import yaml

from kickstart.config import _load_config

_MODEL = {
    "os": "3.2.3",
    "cpu": "68000",
    "sourcerom_crc": "0xDEADBEEF",
    "adf_crc": "0xCAFEBABE",
    "saveprofile": "",
    "template": "stub.j2",
    "amigaos_dir": "/opt/x",
}


def test_models_from_resolves_relative_to_config_file(tmp_path):
    shared = tmp_path / "_shared.yaml"
    shared.write_text(yaml.safe_dump({"models": {"Y": dict(_MODEL)}}))
    main = tmp_path / "main.yaml"
    main.write_text(yaml.safe_dump({"models_from": "_shared.yaml", "modules": []}))
    cfg = _load_config(main)
    assert "Y" in cfg["models"]


def test_models_from_missing_file_dies(tmp_path):
    main = tmp_path / "main.yaml"
    main.write_text(yaml.safe_dump({"models_from": "missing.yaml", "modules": []}))
    with pytest.raises(SystemExit):
        _load_config(main)
