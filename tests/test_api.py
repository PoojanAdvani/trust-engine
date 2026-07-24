"""Tests for the FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from trust_engine.api import create_app


API_KEY = "test-secret-key"


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "api.db"))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def secured_client(tmp_path):
    app = create_app(db_path=str(tmp_path / "api.db"), api_key=API_KEY)
    with TestClient(app) as test_client:
        yield test_client


def test_evaluate_returns_score_and_logs(client):
    payload = {
        "account": {
            "account_age_days": 420,
            "verified_email": True,
            "verified_phone": True,
            "prior_claims": 3,
            "prior_disputes": 0,
        },
        "claim": {"amount": 1200.0, "has_documentation": True, "days_since_incident": 5},
        "risk": {"flags": {"ip_mismatch": 0.3}},
    }

    response = client.post("/evaluate", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert 0.0 <= body["value"] <= 100.0
    assert body["band"] in {"low", "medium", "high"}
    assert {r["name"] for r in body["results"]} == {
        "account_history",
        "claim_details",
        "risk_flags",
    }
    assert body["evaluation_id"] >= 1

    # The evaluation was persisted and is retrievable.
    fetched = client.get(f"/evaluations/{body['evaluation_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["score"] == body["value"]


def test_evaluate_accepts_empty_body(client):
    response = client.post("/evaluate", json={})
    assert response.status_code == 200
    assert "value" in response.json()


def test_get_missing_evaluation_returns_404(client):
    assert client.get("/evaluations/12345").status_code == 404


def test_list_evaluations(client):
    client.post("/evaluate", json={})
    client.post("/evaluate", json={})
    listed = client.get("/evaluations").json()
    assert len(listed) == 2


def test_swagger_docs_available(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    schema = client.get("/openapi.json").json()
    assert "/evaluate" in schema["paths"]


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"


# --- Authentication --------------------------------------------------------


def test_evaluate_rejected_without_api_key(secured_client):
    response = secured_client.post("/evaluate", json={})
    assert response.status_code == 401


def test_evaluate_rejected_with_wrong_api_key(secured_client):
    response = secured_client.post(
        "/evaluate", json={}, headers={"X-API-Key": "wrong"}
    )
    assert response.status_code == 401


def test_evaluate_allowed_with_correct_api_key(secured_client):
    response = secured_client.post(
        "/evaluate", json={}, headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    assert "value" in response.json()


def test_evaluations_endpoints_require_api_key(secured_client):
    assert secured_client.get("/evaluations").status_code == 401
    assert secured_client.get("/evaluations/1").status_code == 401

    authed = {"X-API-Key": API_KEY}
    assert secured_client.get("/evaluations", headers=authed).status_code == 200


def test_health_is_public_when_secured(secured_client):
    response = secured_client.get("/health")
    assert response.status_code == 200


def test_docs_public_when_secured(secured_client):
    assert secured_client.get("/docs").status_code == 200
