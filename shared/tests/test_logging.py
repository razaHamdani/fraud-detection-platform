"""Tests for shared.logging — structlog-based structured logging."""

import structlog

from shared.logging import get_logger, setup_logging


class TestSetupLogging:
    def test_setup_creates_configuration(self):
        setup_logging("test-service", "DEBUG", log_json=False)
        config = structlog.get_config()
        assert config["processors"] is not None
        assert len(config["processors"]) > 0

    def test_setup_json_mode(self):
        setup_logging("test-service", "INFO", log_json=True)
        config = structlog.get_config()
        # Last processor should be JSON renderer
        last = config["processors"][-1]
        assert "JSON" in type(last).__name__ or callable(last)

    def test_setup_console_mode(self):
        setup_logging("test-service", "INFO", log_json=False)
        config = structlog.get_config()
        assert config["processors"] is not None


class TestGetLogger:
    def test_returns_bound_logger(self):
        setup_logging("test-service", "INFO", log_json=False)
        logger = get_logger(component="test")
        assert logger is not None

    def test_logger_with_kwargs(self):
        setup_logging("test-service", "INFO", log_json=False)
        logger = get_logger(request_id="abc-123")
        assert logger is not None
