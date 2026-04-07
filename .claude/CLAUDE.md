# Fraud Detection Platform

Real-time fraud detection and prevention platform.

**Tech Stack**: Python 3.11+, FastAPI, PostgreSQL, Redis, Neo4j, scikit-learn, XGBoost

## Architecture

Event-driven microservices connected via Redis Streams:

| Service | Port | Role | Dependencies |
|---------|------|------|-------------|
| stream-ingester | 8001 | Ingests transactions via REST, publishes to stream | Redis |
| feature-engine | 8002 | Enriches transactions with velocity, geo, graph features | Redis, Neo4j |
| risk-scorer | 8003 | Scores transactions using ML model + rules engine | Redis, PostgreSQL |
| decision-api | 8004 | REST API for decisions, sync scoring, explainability | Redis, PostgreSQL |
| feedback-service | 8005 | Processes chargebacks, adjusts scoring weights | Redis, PostgreSQL |

**Data flow**: stream-ingester -> `txn:incoming` stream -> feature-engine -> `txn:enriched` stream -> risk-scorer -> stores decision in Redis + PostgreSQL -> decision-api serves lookups

**Shared library** (`shared/src/shared/`): Models, config, logging, streams, feature store, health checks, middleware.

## Development

```bash
# Start infrastructure
docker-compose up -d redis postgres neo4j

# Start all services
docker-compose up

# Run database migrations
python migrations/run_migrations.py
```

Environment variables: see `.env.example`. Key vars: `REDIS_URL`, `POSTGRES_DSN`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`.

## Testing

```bash
# Run all unit tests
pytest

# Run specific service tests
pytest services/decision-api/

# Run integration tests (requires Docker services running)
pytest -m integration

# Run with coverage
pytest --cov
```

## Conventions

- **TDD**: Write tests first, then implementation
- **Logging**: Use `shared.logging.get_logger()` and `shared.logging.setup_logging()` -- never `structlog.get_logger()` directly
- **Lifespan pattern**: All services use FastAPI `@asynccontextmanager` lifespan for startup/shutdown
- **Stream naming**: `txn:incoming`, `txn:enriched` (colon-separated, lowercase)
- **Health checks**: All services use `shared.health.HealthChecker` for dependency-aware health (`healthy`/`degraded`)
- **Request tracing**: All services use `shared.middleware.RequestIdMiddleware` for `x-request-id` propagation
- **State management**: Services with shared mutable state use a `state.py` module (decision-api, feedback-service). Others use `app.state`
- **Config**: Centralized via `shared.config.Settings` (pydantic-settings), loaded from env vars
