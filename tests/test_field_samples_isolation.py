"""Le générateur manuel conserve son défaut ; pytest choisit une destination."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.mark.parametrize("explicit", [False, True])
def test_field_samples_destination(tmp_path, monkeypatch, explicit):
    path = Path(__file__).resolve().parents[1] / "benchmarks/make_field_samples.py"
    spec = importlib.util.spec_from_file_location("field_samples_isoles", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    default = tmp_path / "default"
    monkeypatch.setattr(module, "SAMPLES_DIR", default)
    output = tmp_path / "explicit" if explicit else default
    result = module.make_field_samples(output) if explicit else module.make_field_samples()
    assert len(result) == 16
    assert all(v["synthetic"] is True for v in result.values())
    assert json.loads((output / "ground_truth.json").read_text()) == result
    assert all((output / name).is_file() for name in result)
    assert module.SAMPLES_DIR == default
    if explicit:
        assert not default.exists()
