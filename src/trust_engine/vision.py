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
import math
import threading
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from .models import ImageAnalysis
from .settings import Settings

if TYPE_CHECKING:  # import only for type checkers; runtime imports stay lazy
    import numpy as np


def _clamp01(value: float) -> float:
    """Constrain ``value`` to ``[0.0, 1.0]``."""
    return max(0.0, min(1.0, value))


def _sigmoid(x: float) -> float:
    """Numerically stable logistic sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    z = math.exp(x)
    return z / (1.0 + z)


def _average_hash(image_bytes: bytes) -> str:
    """Compute a 64-bit average-hash perceptual hash as 16 hex chars.

    Shared by :class:`AverageHashVisionProvider` and :class:`OnnxVisionProvider`
    so both produce a hash usable by cross-claim reuse detection. Lazy-imports
    Pillow.
    """
    from io import BytesIO

    from PIL import Image

    with Image.open(BytesIO(image_bytes)) as img:
        small = img.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
        # "L" mode yields one byte per pixel; tobytes avoids getdata's
        # deprecation and is stable across Pillow versions.
        pixels = list(small.tobytes())

    mean = sum(pixels) / len(pixels)
    bits = 0
    for pixel in pixels:
        bits = (bits << 1) | (1 if pixel > mean else 0)
    return format(bits, "016x")  # 64 bits -> 16 hex chars


def _decode_rgb(image_bytes: bytes) -> np.ndarray:
    """Decode image bytes to an RGB ``uint8`` HxWx3 numpy array (lazy imports)."""
    from io import BytesIO

    import numpy as np
    from PIL import Image

    with Image.open(BytesIO(image_bytes)) as img:
        return np.asarray(img.convert("RGB"), dtype=np.uint8)


def _heuristic_features(image_rgb: np.ndarray) -> tuple[float, float]:
    """Estimate (damage_score, synthetic_score) with classic CV heuristics.

    - ``damage_score`` from Canny **edge density**: damaged / crumpled / spoiled
      items tend to be edge-dense.
    - ``synthetic_score`` from **low high-frequency detail** (variance of the
      Laplacian): AI-generated or heavily smoothed images carry less fine texture.

    These are deliberately simple, deterministic proxies used when no trained
    model is available. Lazy-imports OpenCV/numpy.
    """
    import cv2
    import numpy as np

    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

    edges = cv2.Canny(gray, 100, 200)
    edge_density = float(np.count_nonzero(edges)) / edges.size
    # Edge density rarely exceeds ~0.25 for photos; scale so that saturates to 1.
    damage_score = _clamp01(edge_density * 4.0)

    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    # High texture variance -> authentic; low -> more "synthetic". 500 is a
    # reasonable saturation point for 8-bit photos.
    synthetic_score = _clamp01(1.0 - lap_var / 500.0)

    return damage_score, synthetic_score


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


class AverageHashVisionProvider:
    """Produces a real 64-bit perceptual hash (average hash) using Pillow.

    Unlike the stub's crypto-derived hash, an average hash is *perceptual*: two
    visually similar images (resized, recompressed) yield hashes a small Hamming
    distance apart, which is what cross-claim near-duplicate detection needs.
    Lazy-imports :mod:`PIL` so the class exists without the ``vision`` extra.

    It only computes a hash; the fraud/condition sub-scores are left at ``0.0``
    (cross-claim reuse is decided by the database lookup, not this provider).
    """

    name = "ahash"

    def analyze(
        self, image_bytes: bytes, *, content_type: str | None = None
    ) -> ImageAnalysis:
        return ImageAnalysis(
            analyzed=True,
            phash=_average_hash(image_bytes),
            provider=self.name,
            notes="average-hash perceptual hash (64-bit)",
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
    """Provider that runs a local ONNX model, with a heuristic fallback.

    When ``model_path`` points at a loadable ONNX model, the image is decoded,
    preprocessed to a normalized ``1x3x224x224`` tensor, and run through an
    :class:`onnxruntime.InferenceSession`; outputs map to ``damage_score`` (index
    0) and ``synthetic_score`` (index 1) via a sigmoid. When no model is
    configured, or loading/inference fails, it falls back to deterministic
    OpenCV/Pillow heuristic features (see :func:`_heuristic_features`) and records
    the reason in ``notes`` — a return-photo request never hard-fails on a model
    misconfiguration.

    All heavy imports (onnxruntime, OpenCV, Pillow, numpy) are lazy, so the class
    can be constructed and imported without the ``vision`` extra installed. The
    session is created lazily on first :meth:`analyze` so construction never
    touches the model file.
    """

    name = "onnx"
    INPUT_SIZE = 224
    # ImageNet normalization (standard for most vision backbones).
    _MEAN = (0.485, 0.456, 0.406)
    _STD = (0.229, 0.224, 0.225)

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or ""
        self._session = None
        self._session_failed = False
        self._load_error = ""
        self._lock = threading.Lock()

    def analyze(
        self, image_bytes: bytes, *, content_type: str | None = None
    ) -> ImageAnalysis:
        phash = _average_hash(image_bytes)
        image = _decode_rgb(image_bytes)

        session = self._get_session()
        if session is not None:
            try:
                damage, synthetic = self._infer(session, image)
                notes = f"onnx inference ({self.model_path})"
                return ImageAnalysis(
                    analyzed=True,
                    damage_score=damage,
                    synthetic_score=synthetic,
                    phash=phash,
                    provider=self.name,
                    notes=notes,
                )
            except Exception as exc:  # runtime inference failure -> heuristics
                damage, synthetic = _heuristic_features(image)
                notes = f"onnx inference failed: {exc}; used heuristics"
                return ImageAnalysis(
                    analyzed=True,
                    damage_score=damage,
                    synthetic_score=synthetic,
                    phash=phash,
                    provider=self.name,
                    notes=notes,
                )

        # No usable session: heuristic features.
        damage, synthetic = _heuristic_features(image)
        if not self.model_path:
            notes = "no model configured; used heuristic features"
        else:
            notes = f"onnx load failed: {self._load_error}; used heuristics"
        return ImageAnalysis(
            analyzed=True,
            damage_score=damage,
            synthetic_score=synthetic,
            phash=phash,
            provider=self.name,
            notes=notes,
        )

    def _get_session(self):
        """Lazily create and cache the InferenceSession; None if unavailable."""
        if self._session is not None or self._session_failed or not self.model_path:
            return self._session
        with self._lock:
            if self._session is None and not self._session_failed:
                try:
                    import onnxruntime

                    self._session = onnxruntime.InferenceSession(
                        self.model_path, providers=["CPUExecutionProvider"]
                    )
                except Exception as exc:  # missing file, bad graph, etc.
                    self._session_failed = True
                    self._load_error = str(exc)
        return self._session

    def _preprocess(self, image_rgb: np.ndarray) -> np.ndarray:
        import numpy as np
        from PIL import Image

        resized = Image.fromarray(image_rgb).resize(
            (self.INPUT_SIZE, self.INPUT_SIZE), Image.Resampling.BILINEAR
        )
        arr = np.asarray(resized, dtype=np.float32) / 255.0  # HxWx3 in [0,1]
        mean = np.array(self._MEAN, dtype=np.float32)
        std = np.array(self._STD, dtype=np.float32)
        arr = (arr - mean) / std
        arr = np.transpose(arr, (2, 0, 1))  # HWC -> CHW
        return arr[np.newaxis, :, :, :]  # add batch -> (1, 3, 224, 224)

    def _infer(self, session, image_rgb: np.ndarray) -> tuple[float, float]:
        import numpy as np

        tensor = self._preprocess(image_rgb)
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: tensor})

        vec = np.asarray(outputs[0]).flatten()
        # Contract: index 0 = damage logit, index 1 = synthetic logit.
        damage = _sigmoid(float(vec[0]))
        synthetic = _sigmoid(float(vec[1])) if vec.size > 1 else 0.0
        return _clamp01(damage), _clamp01(synthetic)


def get_vision_provider(settings: Settings) -> VisionProvider:
    """Select a vision provider from settings, defaulting to the stub."""
    provider = (settings.vision_provider or "stub").lower()

    if provider == "stub":
        return StubVisionProvider()
    if provider == "ahash":
        return AverageHashVisionProvider()
    if provider == "cloud":
        return CloudVisionProvider(
            api_url=settings.vision_api_url or "",
            api_key=settings.vision_api_key,
        )
    if provider == "onnx":
        # A missing model_path is allowed: the provider falls back to heuristics.
        return OnnxVisionProvider(model_path=settings.vision_model_path)

    raise ValueError(
        f"Unknown vision provider '{settings.vision_provider}'. "
        "Expected one of: stub, ahash, cloud, onnx."
    )
