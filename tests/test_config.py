"""Tests for YAML-driven engine configuration."""

import pytest

from trust_engine.config import (
    DEFAULT_BAND_THRESHOLDS,
    load_config,
)

CONFIG_YAML = """
signals:
  account_history:
    weight: 2.0
    maturity_days: 180
  risk_flags:
    weight: 3.0
bands:
  medium_min: 30.0
  high_min: 80.0
"""


def test_missing_file_falls_back_to_defaults(tmp_path):
    config = load_config(tmp_path / "does_not_exist.yaml")
    assert config.band_thresholds == DEFAULT_BAND_THRESHOLDS
    # 3 core signals + 2 image signals.
    assert len(config.signals) == 5


def test_weights_and_bands_loaded(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(CONFIG_YAML, encoding="utf-8")

    config = load_config(path)

    weights = {s.name: s.weight for s in config.signals}
    assert weights == {"account_history": 2.0, "risk_flags": 3.0}
    assert config.band_thresholds == (30.0, 80.0)


def test_signal_tuning_params_applied(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(CONFIG_YAML, encoding="utf-8")

    config = load_config(path)
    account_signal = next(s for s in config.signals if s.name == "account_history")
    assert account_signal.maturity_days == 180


def test_unknown_signal_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("signals:\n  bogus:\n    weight: 1.0\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)


def test_invalid_param_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "signals:\n  risk_flags:\n    weight: 1.0\n    nonsense: 5\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_config(path)
