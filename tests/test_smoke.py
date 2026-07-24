"""Smoke tests to verify the package imports and exposes a version."""

import trust_engine


def test_version_is_exposed():
    assert isinstance(trust_engine.__version__, str)
    assert trust_engine.__version__
