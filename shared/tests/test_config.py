"""Tests for shared.config — Settings with env-based loading."""

import os

from shared.config import Settings, get_settings


class TestSettings:
    def test_defaults_load(self):
        s = Settings()
        assert s.service_name == "fraud-service"
        assert s.redis_url == "redis://localhost:6379"
        assert s.postgres_dsn == "postgresql://fraud_user:fraud_pass@localhost:5432/fraud_detection"
        assert s.neo4j_uri == "bolt://localhost:7687"
        assert s.neo4j_user == "neo4j"
        assert s.neo4j_password == "fraud_pass"
        assert s.log_level == "INFO"
        assert s.log_json is True

    def test_env_vars_override(self, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://custom:6380")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        s = Settings()
        assert s.redis_url == "redis://custom:6380"
        assert s.log_level == "DEBUG"

    def test_service_name_from_env(self, monkeypatch):
        monkeypatch.setenv("SERVICE_NAME", "my-api")
        s = Settings()
        assert s.service_name == "my-api"

    def test_extra_fields_ignored(self, monkeypatch):
        monkeypatch.setenv("UNKNOWN_FIELD", "whatever")
        s = Settings()  # should not raise
        assert s.service_name == "fraud-service"


class TestGetSettings:
    def test_returns_settings_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)
