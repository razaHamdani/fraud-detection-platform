"""Application settings with environment variable loading."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for fraud detection services."""

    service_name: str = "fraud-service"
    redis_url: str = "redis://localhost:6379"
    postgres_dsn: str = "postgresql://fraud_user:fraud_pass@localhost:5432/fraud_detection"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "fraud_pass"
    log_level: str = "INFO"
    log_json: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
