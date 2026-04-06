"""Structured logging setup using structlog."""

import logging

import structlog
from structlog import BoundLogger


def setup_logging(
    service_name: str, log_level: str = "INFO", log_json: bool = True
) -> None:
    """Configure structlog with standard processors.

    Args:
        service_name: Name bound to all log entries via contextvars.
        log_level: Python log level string (DEBUG, INFO, etc.).
        log_json: If True, render as JSON; otherwise use console renderer.
    """
    renderer = (
        structlog.processors.JSONRenderer()
        if log_json
        else structlog.dev.ConsoleRenderer()
    )

    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        renderer,
    ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )

    # Bind service name via contextvars so all loggers include it
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(service=service_name)


def get_logger(**kwargs: object) -> BoundLogger:
    """Return a bound structlog logger with optional initial bindings."""
    return structlog.get_logger(**kwargs)
