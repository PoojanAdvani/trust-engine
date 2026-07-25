"""Tests for vision providers and the provider factory."""

from pathlib import Path

import pytest

from trust_engine.models import ImageAnalysis
from trust_engine.settings import Settings
from trust_engine.vision import (
    CloudVisionProvider,
    OnnxVisionProvider,
    StubVisionProvider,
    get_vision_provider,
)


def test_image_analysis_defaults_are_neutral():
    image = ImageAnalysis()
    assert image.analyzed is False
    assert image.damage_score == 0.0
    assert image.synthetic_score == 0.0
    assert image.edited_score == 0.0
    assert image.reused_score == 0.0


def test_stub_is_deterministic():
    provider = StubVisionProvider()
    a = provider.analyze(b"same-bytes", content_type="image/jpeg")
    b = provider.analyze(b"same-bytes", content_type="image/jpeg")
    assert a == b
    assert a.analyzed is True
    assert a.provider == "stub"
    assert a.phash


def test_stub_varies_with_input():
    provider = StubVisionProvider()
    a = provider.analyze(b"one")
    b = provider.analyze(b"two")
    assert a != b


def test_stub_scores_are_normalized():
    provider = StubVisionProvider()
    result = provider.analyze(b"arbitrary-image-bytes")
    for value in (
        result.damage_score,
        result.synthetic_score,
        result.edited_score,
        result.reused_score,
    ):
        assert 0.0 <= value <= 1.0


def test_factory_defaults_to_stub():
    provider = get_vision_provider(Settings(_env_file=None))
    assert isinstance(provider, StubVisionProvider)


def test_factory_selects_cloud_and_onnx():
    cloud = get_vision_provider(
        Settings(_env_file=None, vision_provider="cloud", vision_api_url="http://x")
    )
    assert isinstance(cloud, CloudVisionProvider)

    onnx = get_vision_provider(
        Settings(_env_file=None, vision_provider="onnx", vision_model_path="m.onnx")
    )
    assert isinstance(onnx, OnnxVisionProvider)


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError):
        get_vision_provider(Settings(_env_file=None, vision_provider="bogus"))


def test_cloud_requires_url():
    with pytest.raises(ValueError):
        CloudVisionProvider(api_url="")


@pytest.mark.vision
def test_average_hash_is_perceptual():
    """The aHash provider yields perceptually-meaningful hashes (needs Pillow)."""
    image_mod = pytest.importorskip("PIL.Image")
    from io import BytesIO

    from trust_engine.reuse import hamming_distance
    from trust_engine.vision import AverageHashVisionProvider

    def gradient_png(size: int = 64, invert: bool = False) -> bytes:
        img = image_mod.new("L", (size, size))
        data = []
        for _y in range(size):
            for x in range(size):
                v = int(255 * x / size)
                data.append(255 - v if invert else v)
        img.putdata(data)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    provider = AverageHashVisionProvider()
    a = provider.analyze(gradient_png())
    b = provider.analyze(gradient_png())
    resized = provider.analyze(gradient_png(size=128))
    inverted = provider.analyze(gradient_png(invert=True))

    assert len(a.phash) == 16  # 64-bit hash
    assert a.phash == b.phash  # identical images -> identical hash
    assert hamming_distance(a.phash, resized.phash) <= 8  # near-duplicate stays close
    assert hamming_distance(a.phash, inverted.phash) >= 16  # different image is far


# --- OnnxVisionProvider (Phase 9) ------------------------------------------

TINY_MODEL = Path(__file__).parent / "fixtures" / "tiny.onnx"


def _photo_png(seed: int = 0) -> bytes:
    """A small RGB PNG with some texture (needs Pillow)."""
    image_mod = pytest.importorskip("PIL.Image")
    from io import BytesIO

    img = image_mod.new("RGB", (64, 64))
    px = img.load()
    for y in range(64):
        for x in range(64):
            px[x, y] = ((x * 4 + seed) % 256, (y * 4) % 256, ((x + y) * 2) % 256)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _assert_valid_features(result):
    assert result.analyzed is True
    assert result.provider == "onnx"
    assert 0.0 <= result.damage_score <= 1.0
    assert 0.0 <= result.synthetic_score <= 1.0
    assert len(result.phash) == 16


@pytest.mark.vision
def test_onnx_heuristic_fallback_without_model():
    pytest.importorskip("cv2")
    result = OnnxVisionProvider(model_path=None).analyze(_photo_png())
    _assert_valid_features(result)
    assert "heuristic" in result.notes.lower()


@pytest.mark.vision
def test_onnx_inference_with_model():
    pytest.importorskip("onnxruntime")
    assert TINY_MODEL.exists(), "run tests/fixtures/generate_tiny_onnx.py"

    provider = OnnxVisionProvider(model_path=str(TINY_MODEL))
    photo = _photo_png()
    result = provider.analyze(photo)
    _assert_valid_features(result)
    assert "onnx inference" in result.notes.lower()

    # Deterministic for identical input.
    again = provider.analyze(photo)
    assert again.damage_score == result.damage_score
    assert again.synthetic_score == result.synthetic_score


@pytest.mark.vision
def test_onnx_bad_model_path_falls_back():
    pytest.importorskip("cv2")
    pytest.importorskip("onnxruntime")
    result = OnnxVisionProvider(model_path="/no/such/model.onnx").analyze(_photo_png())
    _assert_valid_features(result)
    assert "load failed" in result.notes.lower()


@pytest.mark.vision
def test_onnx_distinct_inputs_differ():
    pytest.importorskip("onnxruntime")
    provider = OnnxVisionProvider(model_path=str(TINY_MODEL))
    a = provider.analyze(_photo_png(seed=0))
    b = provider.analyze(_photo_png(seed=99))
    # Different images -> different perceptual hash (model output may vary too).
    assert a.phash != b.phash
