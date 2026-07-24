"""Tests for environment-driven settings."""

from trust_engine.settings import Settings


def test_defaults_when_unset(monkeypatch):
    for var in ("TRUST_ENGINE_CONFIG_PATH", "TRUST_ENGINE_DB_PATH", "TRUST_ENGINE_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    settings = Settings(_env_file=None)
    assert settings.config_path == "config.yaml"
    assert settings.db_path == "trust_engine.db"
    assert settings.api_key is None


def test_reads_environment(monkeypatch):
    monkeypatch.setenv("TRUST_ENGINE_CONFIG_PATH", "/etc/te/config.yaml")
    monkeypatch.setenv("TRUST_ENGINE_DB_PATH", "/var/te/audit.db")
    monkeypatch.setenv("TRUST_ENGINE_API_KEY", "s3cret")

    settings = Settings(_env_file=None)
    assert settings.config_path == "/etc/te/config.yaml"
    assert settings.db_path == "/var/te/audit.db"
    assert settings.api_key == "s3cret"
