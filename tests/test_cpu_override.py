"""A config's `cpu` key replaces the model's CPU for row selection."""

from __future__ import annotations

from types import SimpleNamespace

from kickstart.build import _effective_cpu


def test_config_cpu_replaces_model_cpu():
    cfg = SimpleNamespace(config={"cpu": "68080"})
    assert _effective_cpu(cfg, {"cpu": "68000"}) == "68080"


def test_model_cpu_is_the_default():
    cfg = SimpleNamespace(config={})
    assert _effective_cpu(cfg, {"cpu": "68000"}) == "68000"
