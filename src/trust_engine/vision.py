"""Pluggable vision providers that extract fraud/condition features from photos.

A :class:`VisionProvider` turns raw image bytes into an
:class:`~trust_engine.models.ImageAnalysis` feature object. The heavy/remote work
lives here (called upstream in the async API layer) so the scoring
:mod:`~trust_engine.signals` stay pure and synchronous.

The default :class:`StubVisionProvider` has no third-party dependencies and is
deterministic, so it is safe for local development and tests. The cloud and ONNX
providers lazy-import their heavy dependencies (installed via the ``vision``
extra) so importing this module never requires them.
"""

from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable

from .models import ImageAnalysis
from .settings import Settings


@runtime_checkable
class VisionProvider(Protocol):
    """Protocol implemented by every vision backend."""

    name: str

    def analyze(
        self, image_bytes: bytes, *, content_type: str | None = None
    ) -> ImageAnalysis: ...


class StubVisionProvider:
    """Dependency-free, deterministic provider for dev and tests.

    Derives pseudo-features from a SHA-256 digest of the image bytes so identical
    inputs always yield identical output. It does *not* perform real vision
    analysis — it exists so the full pipeline (upload → features → signals →
    score → audit) can run and be tested without any ML stack.
    """

    name = "stub"

    def analyze(
        self, image_bytes: bytes, *, content_type: str | None = None
    ) -> ImageAnalysis:
        digest = hashlib.sha256(image_bytes).digest()

        # Map distinct digest bytes into [0, 1) so the four sub-scores vary
        # independently but deterministically with the input.
        def _score(index: int) -> float:
            return digest[index] / 255.0

        return ImageAnalysis(
            analyzed=True,
            damage_score=round(_score(0), 4),
            synthetic_score=round(_score(1), 4),
            edited_score=round(_score(2), 4),
            reused_score=round(_score(3), 4),
            phash=digest.hex()[:16],
            provider=self.name,
            notes="stub analysis (deterministic, not a real vision model)",
        )


class CloudVisionProvider:
    """Provider that calls an external HTTP vision API.

    Lazy-imports :mod:`httpx` so this class can be constructed without the
    ``vision`` extra installed; the import only happens on the first
    :meth:`analyze` call.
    """

    name = "cloud"

    def __init__(self, api_url: str, api_key: str | None = None, timeout: float = 10.0) -> None:
        if not api_url:
            raise ValueError("CloudVisionProvider requires vision_api_url")
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout

    def analyze(
        self, image_bytes: bytes, *, content_type: str | None = None
    ) -> ImageAnalysis:
        import httpx  # lazy: only needed when the cloud provider is actually used

        headers = {"Content-Type": content_type or "application/octet-stream"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = httpx.post(
            self.api_url, content=image_bytes, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        return ImageAnalysis(
            analyzed=True,
            damage_score=float(data.get("damage_score", 0.0)),
            synthetic_score=float(data.get("synthetic_score", 0.0)),
            edited_score=float(data.get("edited_score", 0.0)),
            reused_score=float(data.get("reused_score", 0.0)),
            phash=str(data.get("phash", "")),
            provider=self.name,
            notes=str(data.get("notes", "")),
        )


class OnnxVisionProvider:
    """Provider that runs a local ONNX model.

    Lazy-imports :mod:`onnxruntime`/:mod:`PIL` so the class can exist without the
    ``vision`` extra. The concrete model I/O is intentionally left as a follow-up
    (see the phase plan) — this establishes the seam and configuration.
    """

    name = "onnx"

    def __init__(self, model_path: str) -> None:
        if not model_path:
            raise ValueError("OnnxVisionProvider requires vision_model_path")
        self.model_path = model_path

    def analyze(
        self, image_bytes: bytes, *, content_type: str | None = None
    ) -> ImageAnalysis:  # pragma: no cover - requires the vision extra + a model
        import onnxruntime  # noqa: F401  lazy heavy import

        raise NotImplementedError(
            "OnnxVisionProvider.analyze is a follow-up; configure a model and "
            "map its outputs to ImageAnalysis."
        )


def get_vision_provider(settings: Settings) -> VisionProvider:
    """Select a vision provider from settings, defaulting to the stub."""
    provider = (settings.vision_provider or "stub").lower()

    if provider == "stub":
        return StubVisionProvider()
    if provider == "cloud":
        return CloudVisionProvider(
            api_url=settings.vision_api_url or "",
            api_key=settings.vision_api_key,
        )
    if provider == "onnx":
        return OnnxVisionProvider(model_path=settings.vision_model_path or "")

    raise ValueError(
        f"Unknown vision provider '{settings.vision_provider}'. "
        "Expected one of: stub, cloud, onnx."
    )
