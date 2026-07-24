"""Load engine configuration (signal weights, band cutoffs) from a YAML file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .signals import (
    AccountHistorySignal,
    ClaimDetailsSignal,
    RiskFlagsSignal,
    Signal,
    default_signals,
)

# Maps a signal name in config.yaml to its implementation.
SIGNAL_REGISTRY: dict[str, type] = {
    "account_history": AccountHistorySignal,
    "claim_details": ClaimDetailsSignal,
    "risk_flags": RiskFlagsSignal,
}

DEFAULT_BAND_THRESHOLDS: tuple[float, float] = (40.0, 70.0)
DEFAULT_CONFIG_PATH = "config.yaml"


@dataclass(frozen=True)
class EngineConfig:
    """Resolved configuration ready to construct a :class:`TrustEngine`."""

    signals: list[Signal]
    band_thresholds: tuple[float, float]


def _build_signal(name: str, params: dict[str, Any] | None) -> Signal:
    try:
        signal_cls = SIGNAL_REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"Unknown signal '{name}'. Known signals: {sorted(SIGNAL_REGISTRY)}"
        ) from None

    kwargs = dict(params or {})
    try:
        return signal_cls(name=name, **kwargs)
    except TypeError as exc:
        raise ValueError(
            f"Invalid parameters for signal '{name}': {exc}"
        ) from exc


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> EngineConfig:
    """Load configuration from ``path``.

    Falls back to the built-in defaults when the file does not exist, so the
    engine remains usable without a config file.
    """
    config_path = Path(path)
    if not config_path.exists():
        return EngineConfig(default_signals(), DEFAULT_BAND_THRESHOLDS)

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    signals_cfg = data.get("signals") or {}
    if signals_cfg:
        signals = [_build_signal(name, params) for name, params in signals_cfg.items()]
    else:
        signals = default_signals()

    bands = data.get("bands") or {}
    medium_min = float(bands.get("medium_min", DEFAULT_BAND_THRESHOLDS[0]))
    high_min = float(bands.get("high_min", DEFAULT_BAND_THRESHOLDS[1]))

    return EngineConfig(signals=signals, band_thresholds=(medium_min, high_min))
