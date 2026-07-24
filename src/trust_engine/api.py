"""FastAPI application exposing the Trust Engine.

Build an app with :func:`create_app` (used by tests and the ``trust-engine-api``
console script). Interactive Swagger UI is served at ``/docs``.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import __version__
from .config import DEFAULT_CONFIG_PATH, load_config
from .engine import TrustEngine
from .models import AccountHistory, ClaimDetails, RiskFlags, TrustSubject
from .storage import EvaluationStore


# --- Request/response schemas (drive the Swagger docs) ---------------------


class AccountHistoryIn(BaseModel):
    account_age_days: int = 0
    verified_email: bool = False
    verified_phone: bool = False
    prior_claims: int = 0
    prior_disputes: int = 0


class ClaimDetailsIn(BaseModel):
    amount: float = 0.0
    has_documentation: bool = False
    days_since_incident: int = 0
    category: str = "general"


class RiskFlagsIn(BaseModel):
    flags: dict[str, float] = Field(
        default_factory=dict,
        description="Flag name -> severity in [0, 1] (1 is most severe).",
    )


class EvaluateRequest(BaseModel):
    account: AccountHistoryIn = Field(default_factory=AccountHistoryIn)
    claim: ClaimDetailsIn = Field(default_factory=ClaimDetailsIn)
    risk: RiskFlagsIn = Field(default_factory=RiskFlagsIn)


class SignalResultOut(BaseModel):
    name: str
    score: float
    weight: float
    reason: str


class EvaluateResponse(BaseModel):
    evaluation_id: int
    value: float
    band: str
    results: list[SignalResultOut]
    explanation: str


# --- App factory -----------------------------------------------------------


def create_app(
    config_path: str = DEFAULT_CONFIG_PATH,
    db_path: str = "trust_engine.db",
) -> FastAPI:
    """Create a configured FastAPI app backed by an engine and audit store."""
    config = load_config(config_path)
    engine = TrustEngine(config.signals, config.band_thresholds)
    store = EvaluationStore(db_path)

    app = FastAPI(
        title="Trust Engine API",
        version=__version__,
        description="Multi-signal trust scoring with audit history.",
    )
    app.state.engine = engine
    app.state.store = store

    @app.post("/evaluate", response_model=EvaluateResponse, tags=["scoring"])
    def evaluate(request: EvaluateRequest) -> EvaluateResponse:
        """Score a subject across all signals and log the result for audit."""
        subject = TrustSubject(
            account=AccountHistory(**request.account.model_dump()),
            claim=ClaimDetails(**request.claim.model_dump()),
            risk=RiskFlags(flags=dict(request.risk.flags)),
        )
        score = engine.score(subject)
        evaluation_id = store.log(subject, score)
        return EvaluateResponse(
            evaluation_id=evaluation_id,
            value=score.value,
            band=score.band.value,
            results=[SignalResultOut(**asdict(r)) for r in score.results],
            explanation=score.explain(),
        )

    @app.get("/evaluations/{evaluation_id}", tags=["audit"])
    def get_evaluation(evaluation_id: int) -> dict:
        """Fetch a single logged evaluation by id."""
        record = store.get(evaluation_id)
        if record is None:
            raise HTTPException(status_code=404, detail="evaluation not found")
        return record

    @app.get("/evaluations", tags=["audit"])
    def list_evaluations(limit: int = 50) -> list[dict]:
        """List recent evaluations, newest first."""
        return store.list(limit)

    @app.get("/health", tags=["ops"])
    def health() -> dict:
        return {"status": "ok", "evaluations_logged": store.count()}

    return app


def run() -> None:
    """Console-script entry point: serve the app with uvicorn."""
    import uvicorn

    uvicorn.run(
        "trust_engine.api:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
    )
