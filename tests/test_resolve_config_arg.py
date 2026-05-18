import kickstart
from kickstart.paths import CONFIG_DIR

ICONLIB = (CONFIG_DIR / "iconlib.yaml").resolve()


def test_shortname_resolves_to_config_yaml():
    assert kickstart._resolve_config_arg("iconlib") == ICONLIB


def test_shortname_with_extension():
    assert kickstart._resolve_config_arg("iconlib.yaml") == ICONLIB


def test_explicit_relative_path():
    assert kickstart._resolve_config_arg("config/iconlib.yaml") == ICONLIB


def test_explicit_absolute_path():
    assert kickstart._resolve_config_arg(str(ICONLIB)) == ICONLIB


def test_missing_falls_through_for_downstream_error():
    p = kickstart._resolve_config_arg("does_not_exist_profile")
    assert not p.is_file()


def test_discover_excludes_underscore_files():
    names = {p.name for p in kickstart._discover_configs()}
    assert all(not n.startswith("_") for n in names)
    assert "iconlib.yaml" in names
