"""Fails if a frozen file changed without a deliberate re-freeze (see scripts/freeze.py and docs/PREREGISTRATION.md)."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("freeze", ROOT / "scripts" / "freeze.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_frozen_instrument_is_intact():
    fz = _load()
    if not fz.FREEZE.exists():
        pytest.skip("not frozen yet")
    diff = fz.changed(json.loads(fz.FREEZE.read_text()), fz.snapshot())
    assert not diff, f"frozen files changed: {diff}. Re-freeze deliberately and log the deviation."
