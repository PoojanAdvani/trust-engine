"""FastAPI application exposing the Trust Engine.

Build an app with :func:`create_app` (used by tests and the ``trust-engine-api``
console script). Interactive Swagger UI is served at ``/docs``.

The ``/evaluate`` and ``/evaluations`` endpoints require an ``X-API-Key`` header
when an API key is configured (via ``TRUST_ENGINE_API_KEY`` or the ``api_key``
argument). ``/health`` is always public. When no key is configured, auth is
disabled so local development works out of the box.
"""

from __future__ import annotations

import hmac
import json
from dataclasses import asdict

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, ValidationError

from . import __version__
from .config import load_config
from .engine import TrustEngine
from .models import AccountHistory, ClaimDetails, ImageAnalysis, RiskFlags, TrustSubject
from .settings import Settings
from .storage import EvaluationStore
from .vision import VisionProvider, get_vision_provider

API_KEY_HEADER = "X-API-Key"


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
    applicable: bool = True


class EvaluateResponse(BaseModel):
    evaluation_id: int
    value: float
    band: str
    results: list[SignalResultOut]
    explanation: str


class ImageAnalysisOut(BaseModel):
    analyzed: bool
    damage_score: float
    synthetic_score: float
    edited_score: float
    reused_score: float
    phash: str
    provider: str
    notes: str


class ReturnEvaluateResponse(EvaluateResponse):
    image: ImageAnalysisOut


# --- App factory -----------------------------------------------------------


def _parse_context(context_json: str | None) -> EvaluateRequest:
    """Parse the optional multipart context field into an EvaluateRequest."""
    if not context_json:
        return EvaluateRequest()
    try:
        return EvaluateRequest.model_validate_json(context_json)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,  # Unprocessable Content
            detail=f"invalid context_json: {exc.errors()}",
        ) from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=422,  # Unprocessable Content
            detail="context_json must be valid JSON",
        ) from exc


def create_app(
    config_path: str | None = None,
    db_path: str | None = None,
    api_key: str | None = None,
    settings: Settings | None = None,
    vision_provider: VisionProvider | None = None,
) -> FastAPI:
    """Create a configured FastAPI app backed by an engine and audit store.

    Explicit arguments take precedence over environment-derived ``settings``,
    which fall back to their own defaults. ``vision_provider`` can be injected
    (e.g. a fake in tests); otherwise it is selected from ``settings``.
    """
    if settings is None:
        settings = Settings()

    resolved_config_path = config_path or settings.config_path
    resolved_db_path = db_path or settings.db_path
    resolved_api_key = api_key if api_key is not None else settings.api_key
    if vision_provider is None:
        vision_provider = get_vision_provider(settings)

    config = load_config(resolved_config_path)
    engine = TrustEngine(config.signals, config.band_thresholds)
    store = EvaluationStore(resolved_db_path)

    app = FastAPI(
        title="Trust Engine API",
        version=__version__,
        description="Multi-signal trust scoring with audit history.",
    )
    app.state.engine = engine
    app.state.store = store
    app.state.api_key = resolved_api_key
    app.state.vision_provider = vision_provider
    app.state.vision_max_bytes = settings.vision_max_bytes

    # auto_error=False lets us allow open access when no key is configured and
    # still surface an Authorize button in Swagger when one is.
    api_key_scheme = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)

    def require_api_key(provided: str | None = Depends(api_key_scheme)) -> None:
        if resolved_api_key is None:
            return  # authentication disabled
        # Constant-time comparison avoids leaking the key via response timing.
        expected = resolved_api_key.encode("utf-8")
        supplied = (provided or "").encode("utf-8")
        if not provided or not hmac.compare_digest(supplied, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )

    @app.post(
        "/evaluate",
        response_model=EvaluateResponse,
        tags=["scoring"],
        dependencies=[Depends(require_api_key)],
    )
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

    @app.post(
        "/returns/evaluate",
        response_model=ReturnEvaluateResponse,
        tags=["scoring"],
        dependencies=[Depends(require_api_key)],
    )
    async def evaluate_return(
        file: UploadFile = File(..., description="The return photo to verify."),
        context_json: str | None = Form(
            default=None,
            description="Optional JSON matching the /evaluate body (account/claim/risk).",
        ),
    ) -> ReturnEvaluateResponse:
        """Verify a return photo and score it through the full trust pipeline."""
        if not (file.content_type or "").startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="file must be an image (content-type image/*)",
            )

        data = await file.read()
        if len(data) > app.state.vision_max_bytes:
            raise HTTPException(
                status_code=413,  # Content Too Large
                detail=f"image exceeds max size of {app.state.vision_max_bytes} bytes",
            )
        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="empty image upload"
            )

        context = _parse_context(context_json)

        # Run the (possibly blocking) provider off the event loop.
        features = await run_in_threadpool(
            vision_provider.analyze, data, content_type=file.content_type
        )

        subject = TrustSubject(
            account=AccountHistory(**context.account.model_dump()),
            claim=ClaimDetails(**context.claim.model_dump()),
            risk=RiskFlags(flags=dict(context.risk.flags)),
            image=ImageAnalysis(**asdict(features)),
        )
        score = engine.score(subject)
        evaluation_id = store.log(subject, score)
        return ReturnEvaluateResponse(
            evaluation_id=evaluation_id,
            value=score.value,
            band=score.band.value,
            results=[SignalResultOut(**asdict(r)) for r in score.results],
            explanation=score.explain(),
            image=ImageAnalysisOut(**asdict(features)),
        )

    @app.get(
        "/evaluations/{evaluation_id}",
        tags=["audit"],
        dependencies=[Depends(require_api_key)],
    )
    def get_evaluation(evaluation_id: int) -> dict:
        """Fetch a single logged evaluation by id."""
        record = store.get(evaluation_id)
        if record is None:
            raise HTTPException(status_code=404, detail="evaluation not found")
        return record

    @app.get(
        "/evaluations",
        tags=["audit"],
        dependencies=[Depends(require_api_key)],
    )
    def list_evaluations(limit: int = 50) -> list[dict]:
        """List recent evaluations, newest first."""
        return store.list(limit)

    @app.get("/health", tags=["ops"])
    def health() -> dict:
        """Public liveness check (no authentication required)."""
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
