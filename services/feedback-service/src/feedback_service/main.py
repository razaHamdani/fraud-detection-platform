"""Feedback Service: chargeback processing and weight adjustment."""

from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI

from shared.config import get_settings
from shared.logging import setup_logging, get_logger
from shared.models import Chargeback
from feedback_service.chargeback import ChargebackProcessor
from feedback_service import state


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(service_name="feedback-service", log_level=settings.log_level)
    redis = aioredis.from_url(settings.redis_url)
    pg_pool = await asyncpg.create_pool(settings.postgres_dsn)
    state.processor = ChargebackProcessor(pg_pool=pg_pool, redis=redis)
    get_logger().info("feedback-service started")
    yield
    await pg_pool.close()
    await redis.aclose()


app = FastAPI(title="Feedback Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "feedback-service"}


@app.post("/feedback/chargeback")
async def report_chargeback(cb: Chargeback):
    result = await state.processor.process(cb)
    if result:
        return {"status": "processed", "chargeback_id": str(cb.chargeback_id)}
    return {"status": "partial", "detail": "Original decision not found"}
