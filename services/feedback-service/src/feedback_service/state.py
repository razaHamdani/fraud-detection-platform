"""Mutable service state."""

from shared.health import HealthChecker

processor = None
health_checker: HealthChecker | None = None
