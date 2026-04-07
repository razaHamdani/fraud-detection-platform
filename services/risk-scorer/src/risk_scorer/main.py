"""Risk Scorer: consumes enriched transactions, applies scoring + rules, publishes decisions."""

import asyncio
from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI

from shared.config import get_settings
from shared.logging import setup_logging, get_logger
from shared.models import ScoringWeights
from risk_scorer.worker import run_worker

_worker_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_task
    settings = get_settings()
    setup_logging(service_name="risk-scorer", log_level=settings.log_level)

    redis = aioredis.from_url(settings.redis_url)
    pg_pool = await asyncpg.create_pool(settings.postgres_dsn)
    weights = ScoringWeights()  # TODO: load from Postgres

    _worker_task = asyncio.create_task(run_worker(redis, pg_pool, weights))
    get_logger().info("risk-scorer started")
    yield
    _worker_task.cancel()
    await pg_pool.close()
    await redis.aclose()


app = FastAPI(title="Risk Scorer", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "risk-scorer"}
