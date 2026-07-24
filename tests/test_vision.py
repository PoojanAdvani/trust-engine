"""Tests for vision providers and the provider factory."""

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
