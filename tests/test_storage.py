"""Tests for the SQLite evaluation audit store."""

from trust_engine import (
    AccountHistory,
    ClaimDetails,
    RiskFlags,
    TrustEngine,
    TrustSubject,
)
from trust_engine.storage import EvaluationStore


def _subject() -> TrustSubject:
    return TrustSubject(
        account=AccountHistory(account_age_days=100, verified_email=True),
        claim=ClaimDetails(amount=500.0, has_documentation=True),
        risk=RiskFlags(flags={"ip_mismatch": 0.4}),
    )


def test_log_and_get_round_trip(tmp_path):
    store = EvaluationStore(tmp_path / "audit.db")
    subject = _subject()
    score = TrustEngine().score(subject)

    evaluation_id = store.log(subject, score)
    record = store.get(evaluation_id)

    assert record is not None
    assert record["id"] == evaluation_id
    assert record["score"] == score.value
    assert record["band"] == score.band.value
    assert record["payload"]["risk"]["flags"] == {"ip_mismatch": 0.4}
    assert len(record["results"]) == len(score.results)
    assert "created_at" in record


def test_get_missing_returns_none(tmp_path):
    store = EvaluationStore(tmp_path / "audit.db")
    assert store.get(999) is None


def test_list_is_newest_first_and_count(tmp_path):
    store = EvaluationStore(tmp_path / "audit.db")
    engine = TrustEngine()
    ids = [store.log(_subject(), engine.score(_subject())) for _ in range(3)]

    listed = store.list()
    assert [r["id"] for r in listed] == sorted(ids, reverse=True)
    assert store.count() == 3


def test_persists_across_instances(tmp_path):
    db = tmp_path / "audit.db"
    store = EvaluationStore(db)
    store.log(_subject(), TrustEngine().score(_subject()))

    reopened = EvaluationStore(db)
    assert reopened.count() == 1
