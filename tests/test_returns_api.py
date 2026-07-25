"""Tests for the POST /returns/evaluate image-upload endpoint."""

import json

import pytest
from fastapi.testclient import TestClient

from trust_engine.api import create_app
from trust_engine.models import ImageAnalysis

API_KEY = "test-secret-key"


class FakeVisionProvider:
    """Provider returning canned features, so tests need no ML stack."""

    name = "fake"

    def __init__(self, **features):
        self._features = features

    def analyze(self, image_bytes: bytes, *, content_type=None) -> ImageAnalysis:
        defaults = dict(
            analyzed=True,
            damage_score=0.2,
            synthetic_score=0.1,
            edited_score=0.0,
            reused_score=0.0,
            phash="deadbeef",
            provider=self.name,
            notes="fake",
        )
        defaults.update(self._features)
        return ImageAnalysis(**defaults)


def _app(tmp_path, *, api_key=None, provider=None):
    return create_app(
        db_path=str(tmp_path / "returns.db"),
        api_key=api_key,
        vision_provider=provider or FakeVisionProvider(),
    )


@pytest.fixture
def client(tmp_path):
    with TestClient(_app(tmp_path)) as c:
        yield c


def _image_file(content=b"fake-image-bytes", content_type="image/jpeg"):
    return {"file": ("return.jpg", content, content_type)}


def test_returns_evaluate_happy_path(client):
    response = client.post("/returns/evaluate", files=_image_file())
    assert response.status_code == 200

    body = response.json()
    assert 0.0 <= body["value"] <= 100.0
    assert body["band"] in {"low", "medium", "high"}

    names = {r["name"] for r in body["results"]}
    assert {"image_condition", "image_authenticity"} <= names

    assert body["image"]["analyzed"] is True
    assert body["image"]["provider"] == "fake"
    assert body["evaluation_id"] >= 1


def test_returns_evaluate_persists_features(client):
    body = client.post("/returns/evaluate", files=_image_file()).json()
    fetched = client.get(f"/evaluations/{body['evaluation_id']}")
    assert fetched.status_code == 200

    payload = fetched.json()["payload"]
    assert payload["image"]["analyzed"] is True
    assert payload["image"]["damage_score"] == 0.2
    # Raw bytes must never be persisted — only extracted features.
    assert "image_bytes" not in payload["image"]


def test_returns_evaluate_accepts_context_json(client):
    context = {"claim": {"amount": 5000.0, "has_documentation": False}}
    response = client.post(
        "/returns/evaluate",
        files=_image_file(),
        data={"context_json": json.dumps(context)},
    )
    assert response.status_code == 200
    names = {r["name"] for r in response.json()["results"]}
    assert "claim_details" in names


def test_returns_evaluate_rejects_non_image(client):
    response = client.post(
        "/returns/evaluate",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415


def test_returns_evaluate_rejects_oversize(tmp_path):
    app = create_app(
        db_path=str(tmp_path / "returns.db"),
        vision_provider=FakeVisionProvider(),
    )
    app.state.vision_max_bytes = 10  # force the limit
    with TestClient(app) as client:
        response = client.post(
            "/returns/evaluate",
            files=_image_file(content=b"this-is-definitely-more-than-ten-bytes"),
        )
    assert response.status_code == 413


def test_returns_evaluate_rejects_bad_context(client):
    response = client.post(
        "/returns/evaluate",
        files=_image_file(),
        data={"context_json": "{not valid json"},
    )
    assert response.status_code == 422


def test_returns_evaluate_requires_api_key(tmp_path):
    app = _app(tmp_path, api_key=API_KEY)
    with TestClient(app) as client:
        unauth = client.post("/returns/evaluate", files=_image_file())
        assert unauth.status_code == 401

        authed = client.post(
            "/returns/evaluate",
            files=_image_file(),
            headers={"X-API-Key": API_KEY},
        )
        assert authed.status_code == 200


def test_high_fraud_photo_lowers_score(tmp_path):
    """A photo flagged as reused/synthetic should score lower than a clean one."""
    clean_app = _app(tmp_path, provider=FakeVisionProvider(damage_score=0.0))
    with TestClient(clean_app) as client:
        clean = client.post("/returns/evaluate", files=_image_file()).json()

    fraud_provider = FakeVisionProvider(
        damage_score=0.9, synthetic_score=0.9, reused_score=0.9
    )
    fraud_app = create_app(
        db_path=str(tmp_path / "fraud.db"), vision_provider=fraud_provider
    )
    with TestClient(fraud_app) as client:
        fraud = client.post("/returns/evaluate", files=_image_file()).json()

    assert fraud["value"] < clean["value"]


# --- Cross-claim reuse detection (Phase 8) ---------------------------------


class MappedVisionProvider:
    """Maps specific upload bytes to specific phashes for near-dup control."""

    name = "mapped"

    def __init__(self, mapping):
        self.mapping = mapping

    def analyze(self, image_bytes: bytes, *, content_type=None) -> ImageAnalysis:
        return ImageAnalysis(
            analyzed=True, phash=self.mapping[image_bytes], provider=self.name
        )


def _ctx(account_id="", claim_id=""):
    body = {"account": {"account_id": account_id}, "claim": {"claim_id": claim_id}}
    return {"context_json": json.dumps(body)}


# A fixed-phash provider models "the same photo" regardless of byte encoding.
def _fixed_phash_app(tmp_path, name="dup.db"):
    provider = FakeVisionProvider(
        phash="ffffffffffffffff",
        reused_score=0.0,
        synthetic_score=0.1,
        edited_score=0.0,
        damage_score=0.0,
    )
    return create_app(db_path=str(tmp_path / name), vision_provider=provider)


def test_duplicate_across_accounts_flags_reuse(tmp_path):
    with TestClient(_fixed_phash_app(tmp_path)) as client:
        first = client.post(
            "/returns/evaluate", files=_image_file(), data=_ctx("acctA", "clm1")
        ).json()
        second = client.post(
            "/returns/evaluate", files=_image_file(), data=_ctx("acctB", "clm2")
        ).json()

    assert first["reuse_matches"] == 0
    assert second["reuse_matches"] >= 1
    assert second["image"]["reused_score"] == 1.0
    assert second["value"] < first["value"]

    # The authenticity signal is fully penalized (reused 1.0 -> score 0.0).
    auth = next(r for r in second["results"] if r["name"] == "image_authenticity")
    assert auth["score"] == 0.0


def test_same_account_same_claim_reupload_not_penalized(tmp_path):
    with TestClient(_fixed_phash_app(tmp_path)) as client:
        first = client.post(
            "/returns/evaluate", files=_image_file(), data=_ctx("acctA", "clm1")
        ).json()
        second = client.post(
            "/returns/evaluate", files=_image_file(), data=_ctx("acctA", "clm1")
        ).json()

    assert second["reuse_matches"] == 0
    assert second["image"]["reused_score"] == first["image"]["reused_score"]
    assert second["value"] == first["value"]


def test_different_image_no_match(tmp_path):
    provider = MappedVisionProvider(
        {b"img-a": "ffffffffffffffff", b"img-b": "0000000000000000"}
    )
    app = create_app(db_path=str(tmp_path / "diff.db"), vision_provider=provider)
    with TestClient(app) as client:
        client.post(
            "/returns/evaluate",
            files=_image_file(content=b"img-a"),
            data=_ctx("acctA", "clm1"),
        )
        second = client.post(
            "/returns/evaluate",
            files=_image_file(content=b"img-b"),
            data=_ctx("acctB", "clm2"),
        ).json()

    assert second["reuse_matches"] == 0


def test_near_duplicate_across_accounts_flagged(tmp_path):
    # phashes differ by a single bit -> within the default threshold of 10.
    provider = MappedVisionProvider(
        {b"img-a": "ffffffffffffffff", b"img-b": "fffffffffffffffe"}
    )
    app = create_app(db_path=str(tmp_path / "near.db"), vision_provider=provider)
    with TestClient(app) as client:
        client.post(
            "/returns/evaluate",
            files=_image_file(content=b"img-a"),
            data=_ctx("acctA", "clm1"),
        )
        second = client.post(
            "/returns/evaluate",
            files=_image_file(content=b"img-b"),
            data=_ctx("acctB", "clm2"),
        ).json()

    assert second["reuse_matches"] >= 1
    assert 0.0 < second["image"]["reused_score"] < 1.0
