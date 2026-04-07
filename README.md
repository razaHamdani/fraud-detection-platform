# Fraud Detection Platform

Real-time fraud detection and risk scoring platform. Processes transaction streams, extracts features (velocity, geo anomalies, entity graph), applies weighted scoring + rule engine, and returns approve/hold/block decisions.

## Architecture

Event-driven microservices connected via Redis Streams:

```
POST /transactions
       |
       v
 stream-ingester ──> [stream:raw_transactions] ──> feature-engine ──> [stream:enriched_transactions]
       (8001)                                          (8002)
                                                         |
                                                         v
 decision-api <── Redis cache <── risk-scorer <──────────┘
    (8004)                          (8003)
                                      |
                                      v
                                  PostgreSQL
                                      ^
                                      |
                              feedback-service
                                   (8005)
```

| Service | Port | Role |
|---------|------|------|
| **stream-ingester** | 8001 | REST ingestion, publishes raw transactions to Redis Streams |
| **feature-engine** | 8002 | Extracts velocity, geo, graph, and transaction features in parallel |
| **risk-scorer** | 8003 | Weighted scoring formula + rule engine, persists decisions |
| **decision-api** | 8004 | Sync scoring, decision lookup, explainability, rate limiting |
| **feedback-service** | 8005 | Chargeback processing, EMA-based scoring weight adjustment |

### Infrastructure

| Component | Purpose |
|-----------|---------|
| **Redis 7** | Message broker (Streams), feature store (sorted sets, hashes), decision cache |
| **PostgreSQL 16** | Transactions, decisions, rules, chargebacks, scoring weights |
| **Neo4j 5** | Entity graph (shared devices, IPs, cards) for fraud cluster detection |

### Shared Library

`shared/src/shared/` provides common components used across all services:

- **models.py** -- Pydantic v2 models (Transaction, Decision, FeatureSet, ScoringWeights, etc.)
- **config.py** -- Centralized settings via pydantic-settings
- **streams.py** -- Redis Streams publisher/consumer with Protocol abstractions (Kafka-swappable)
- **feature_store.py** -- Atomic Redis operations via Lua scripts (sliding window counters)
- **health.py** -- Dependency-aware health checker (Redis, Postgres, Neo4j probes)
- **middleware.py** -- Request ID propagation middleware
- **logging.py** -- Structured JSON logging via structlog

## Tech Stack

- **Language**: Python 3.11+ (Docker), 3.10+ (local dev)
- **Framework**: FastAPI with async lifespan context managers
- **Broker**: Redis Streams (Protocol abstractions for future Kafka swap)
- **Databases**: PostgreSQL 16, Neo4j 5, Redis 7
- **ML** (planned): scikit-learn, XGBoost

## Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local test execution)

## Quick Start

```bash
# Clone
git clone git@github.com:razaHamdani/fraud-detection-platform.git
cd fraud-detection-platform

# Copy environment variables
cp .env.example .env

# Start everything
docker compose up --build

# Run database migrations (in another terminal)
docker compose exec risk-scorer python -m migrations.run_migrations
```

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install shared library and all services in dev mode
pip install -e shared/[dev]
pip install -e services/stream-ingester/[dev]
pip install -e services/feature-engine/[dev]
pip install -e services/risk-scorer/[dev]
pip install -e services/decision-api/[dev]
pip install -e services/feedback-service/[dev]

# Start infrastructure only
docker compose up -d redis postgres neo4j

# Run migrations
python migrations/run_migrations.py
python migrations/neo4j_setup.py
```

## Configuration

All services read configuration from environment variables via `shared.config.Settings`:

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `POSTGRES_DSN` | `postgresql://fraud_user:fraud_pass@localhost:5432/fraud_detection` | PostgreSQL connection string |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `fraud_pass` | Neo4j password |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_JSON` | `true` | JSON-formatted log output |

## API Reference

### Decision API (port 8004)

```bash
# Submit transaction for scoring (sync, <50ms target)
curl -X POST http://localhost:8004/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "amount": 99.99,
    "currency": "USD",
    "merchant_id": "merch_001",
    "mcc": "5411",
    "timestamp": "2026-04-07T12:00:00Z",
    "latitude": 40.7128,
    "longitude": -74.006,
    "device_fingerprint": "fp_abc",
    "ip_address": "192.168.1.1"
  }'

# Look up a decision
curl http://localhost:8004/transactions/{txn_id}

# Get scoring explanation (breakdown + triggered rules)
curl http://localhost:8004/explain/{txn_id}
```

### Stream Ingester (port 8001)

```bash
# Submit transaction (async, returns 202)
curl -X POST http://localhost:8001/transactions \
  -H "Content-Type: application/json" \
  -d '{ ... same payload ... }'
```

### Feedback Service (port 8005)

```bash
# Report chargeback (triggers weight adjustment)
curl -X POST http://localhost:8005/feedback/chargeback \
  -H "Content-Type: application/json" \
  -d '{
    "txn_id": "uuid-of-transaction",
    "reason": "unauthorized"
  }'
```

### Health Checks

All services expose `GET /health` returning `{"status": "healthy"}` or `{"status": "degraded"}` with per-dependency status.

## Scoring

### Weighted Formula

Four feature categories, each scored 0.0-1.0, combined with configurable weights:

| Category | Default Weight | Features |
|----------|---------------|----------|
| Velocity | 0.30 | Transaction count (5min, 1hr), amount sum, unique merchants |
| Geo | 0.20 | Distance from last location, travel velocity, country mismatch |
| Device | 0.30 | Shared device count, shared IP count, card-device ratio |
| Graph | 0.20 | Risk cluster membership, shared entity counts (Neo4j) |

**Decision thresholds**: APPROVE < 0.3, HOLD 0.3-0.7, BLOCK > 0.7

### Rule Engine

Post-score rules can override the decision (BLOCK > HOLD > APPROVE):

| Rule | Action | Priority |
|------|--------|----------|
| Impossible travel (geo velocity > 900 km/h) | BLOCK | 100 |
| High amount on first transaction | BLOCK | 90 |
| Shared device count > 5 | HOLD | 80 |

### Weight Adaptation

When chargebacks are reported, scoring weights are adjusted via exponential moving average (EMA) -- categories that correctly identified fraud get higher weight over time.

## Testing

```bash
# Run all unit tests (132 tests)
pytest

# Run specific service
pytest services/risk-scorer/

# Run integration tests (requires Docker services)
pytest -m integration

# Run with coverage
pytest --cov
```

## Database Migrations

```bash
# PostgreSQL (5 tables: transactions, decisions, rules, chargebacks, scoring_weights)
python migrations/run_migrations.py

# Neo4j (uniqueness constraints for User, Card, Device, IP, Merchant)
python migrations/neo4j_setup.py
```

## Project Structure

```
fraud-detection-platform/
├── docker-compose.yml              # All services + infrastructure
├── pyproject.toml                  # Root config (pytest, ruff)
├── .env.example                    # Environment variable template
├── migrations/
│   ├── 001_initial.sql             # PostgreSQL schema + seed data
│   ├── run_migrations.py           # Async migration runner
│   └── neo4j_setup.py             # Neo4j constraint setup
├── shared/                         # Shared library (fraud-shared)
│   ├── src/shared/
│   │   ├── models.py              # Pydantic models
│   │   ├── config.py              # Settings (pydantic-settings)
│   │   ├── streams.py             # Redis Streams pub/sub
│   │   ├── feature_store.py       # Atomic Redis operations (Lua)
│   │   ├── health.py              # Health checker
│   │   ├── middleware.py          # Request ID middleware
│   │   └── logging.py            # Structured logging
│   └── tests/
├── services/
│   ├── stream-ingester/           # Transaction ingestion
│   ├── feature-engine/            # Feature extraction
│   ├── risk-scorer/               # Scoring + rules
│   ├── decision-api/              # REST API
│   └── feedback-service/          # Chargeback processing
└── tests/
    └── integration/               # End-to-end tests
```
