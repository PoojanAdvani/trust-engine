"""Tests for the TrustEngine and its signals."""

import pytest

from trust_engine import (
    AccountHistory,
    ClaimDetails,
    RiskFlags,
    TrustBand,
    TrustEngine,
    TrustSubject,
)
from trust_engine.signals import (
    AccountHistorySignal,
    ClaimDetailsSignal,
    RiskFlagsSignal,
)


def _trusted_subject() -> TrustSubject:
    return TrustSubject(
        account=AccountHistory(
            account_age_days=800,
            verified_email=True,
            verified_phone=True,
            prior_claims=5,
            prior_disputes=0,
        ),
        claim=ClaimDetails(
            amount=100.0,
            has_documentation=True,
            days_since_incident=1,
        ),
        risk=RiskFlags(),
    )


def _risky_subject() -> TrustSubject:
    return TrustSubject(
        account=AccountHistory(
            account_age_days=2,
            verified_email=False,
            verified_phone=False,
            prior_claims=4,
            prior_disputes=4,
        ),
        claim=ClaimDetails(
            amount=50_000.0,
            has_documentation=False,
            days_since_incident=300,
        ),
        risk=RiskFlags(flags={"stolen_device": 1.0, "velocity_abuse": 0.8}),
    )


def test_score_is_bounded():
    engine = TrustEngine()
    for subject in (_trusted_subject(), _risky_subject(), TrustSubject()):
        result = engine.score(subject)
        assert 0.0 <= result.value <= 100.0


def test_trusted_scores_higher_than_risky():
    engine = TrustEngine()
    trusted = engine.score(_trusted_subject())
    risky = engine.score(_risky_subject())
    assert trusted.value > risky.value
    assert trusted.band == TrustBand.HIGH
    assert risky.band == TrustBand.LOW


def test_bands_follow_thresholds():
    engine = TrustEngine(band_thresholds=(40.0, 70.0))
    assert engine._band_for(85.0) == TrustBand.HIGH
    assert engine._band_for(55.0) == TrustBand.MEDIUM
    assert engine._band_for(10.0) == TrustBand.LOW


def test_no_flags_gives_full_risk_score():
    result = RiskFlagsSignal().evaluate(TrustSubject())
    assert result.score == 1.0


def test_severe_flags_drive_risk_score_down():
    subject = TrustSubject(risk=RiskFlags(flags={"a": 1.0, "b": 1.0}))
    result = RiskFlagsSignal().evaluate(subject)
    assert result.score == 0.0


def test_results_include_every_signal():
    engine = TrustEngine()
    result = engine.score(TrustSubject())
    names = {r.name for r in result.results}
    # Image signals are excluded when no photo was analyzed.
    assert names == {"account_history", "claim_details", "risk_flags"}


def test_signal_scores_are_normalized():
    subject = _risky_subject()
    for signal in (AccountHistorySignal(), ClaimDetailsSignal(), RiskFlagsSignal()):
        result = signal.evaluate(subject)
        assert 0.0 <= result.score <= 1.0


def test_empty_signal_list_rejected():
    with pytest.raises(ValueError):
        TrustEngine(signals=[])


def test_invalid_thresholds_rejected():
    with pytest.raises(ValueError):
        TrustEngine(band_thresholds=(80.0, 50.0))


def test_explain_is_readable():
    result = TrustEngine().score(_trusted_subject())
    text = result.explain()
    assert "Trust score" in text
    assert "account_history" in text
