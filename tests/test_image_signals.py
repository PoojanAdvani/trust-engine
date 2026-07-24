"""Tests for the image condition and authenticity signals."""

from trust_engine import TrustEngine
from trust_engine.models import ImageAnalysis, TrustSubject
from trust_engine.signals import ImageAuthenticitySignal, ImageConditionSignal


def _analyzed(**kwargs) -> TrustSubject:
    return TrustSubject(image=ImageAnalysis(analyzed=True, **kwargs))


def test_condition_neutral_when_not_analyzed():
    result = ImageConditionSignal().evaluate(TrustSubject())
    assert result.applicable is False


def test_authenticity_neutral_when_not_analyzed():
    result = ImageAuthenticitySignal().evaluate(TrustSubject())
    assert result.applicable is False


def test_condition_drops_with_damage():
    clean = ImageConditionSignal().evaluate(_analyzed(damage_score=0.0))
    damaged = ImageConditionSignal().evaluate(_analyzed(damage_score=0.9))
    assert clean.applicable is True
    assert clean.score == 1.0
    assert damaged.score < clean.score
    assert 0.0 <= damaged.score <= 1.0


def test_authenticity_driven_by_worst_component():
    subject = _analyzed(synthetic_score=0.1, edited_score=0.0, reused_score=0.8)
    result = ImageAuthenticitySignal().evaluate(subject)
    # Worst component (reused 0.8) drives the score: 1 - 0.8 = 0.2.
    assert abs(result.score - 0.2) < 1e-9
    assert "reused" in result.reason


def test_analyzed_image_signals_contribute_to_engine():
    engine = TrustEngine()
    subject = _analyzed(damage_score=0.5, synthetic_score=0.5)
    result = engine.score(subject)
    names = {r.name for r in result.results}
    assert {"image_condition", "image_authenticity"} <= names


def test_unanalyzed_image_signals_excluded_from_engine():
    engine = TrustEngine()
    result = engine.score(TrustSubject())
    names = {r.name for r in result.results}
    assert "image_condition" not in names
    assert "image_authenticity" not in names
