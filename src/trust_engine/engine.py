"""The core :class:`TrustEngine` that aggregates signals into a trust score."""

from __future__ import annotations

from collections.abc import Iterable

from .models import TrustBand, TrustScore, TrustSubject
from .signals import Signal, default_signals


class TrustEngine:
    """Combines multiple weighted signals into a single trust score.

    Each configured signal is evaluated against the subject and produces a
    normalized score in ``[0.0, 1.0]``. Those scores are combined as a
    weighted average and scaled to ``0-100``, then bucketed into a
    :class:`~trust_engine.models.TrustBand`.

    Parameters
    ----------
    signals:
        The signals to evaluate. Defaults to
        :func:`~trust_engine.signals.default_signals`.
    band_thresholds:
        ``(medium_min, high_min)`` score cutoffs. Scores below ``medium_min``
        are ``LOW``, below ``high_min`` are ``MEDIUM``, otherwise ``HIGH``.
    """

    def __init__(
        self,
        signals: Iterable[Signal] | None = None,
        band_thresholds: tuple[float, float] = (40.0, 70.0),
    ) -> None:
        self.signals: list[Signal] = (
            list(signals) if signals is not None else default_signals()
        )
        if not self.signals:
            raise ValueError("TrustEngine requires at least one signal")

        medium_min, high_min = band_thresholds
        if not 0.0 <= medium_min <= high_min <= 100.0:
            raise ValueError(
                "band_thresholds must satisfy 0 <= medium_min <= high_min <= 100"
            )
        self.band_thresholds = band_thresholds

    def score(self, subject: TrustSubject) -> TrustScore:
        """Evaluate ``subject`` against all signals and return a TrustScore.

        Signals that report ``applicable=False`` (e.g. image signals with no
        photo) are excluded from the weighted average and from the breakdown.
        """
        evaluated = (signal.evaluate(subject) for signal in self.signals)
        results = tuple(r for r in evaluated if r.applicable)

        total_weight = sum(r.weight for r in results)
        if total_weight <= 0:
            raise ValueError("No applicable signals with positive weight to score")

        weighted = sum(r.score * r.weight for r in results) / total_weight
        value = round(weighted * 100.0, 1)

        return TrustScore(value=value, band=self._band_for(value), results=results)

    def _band_for(self, value: float) -> TrustBand:
        medium_min, high_min = self.band_thresholds
        if value >= high_min:
            return TrustBand.HIGH
        if value >= medium_min:
            return TrustBand.MEDIUM
        return TrustBand.LOW
