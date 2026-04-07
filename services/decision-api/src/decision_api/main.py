"""Decision API: REST endpoints for sync scoring, decision lookup, and explainability."""
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import asyncpg
from fastapi import FastAPI

from shared.config import get_settings
from shared.health import HealthChecker
from shared.logging import setup_logging, get_logger
from shared.middleware import RequestIdMiddleware
from decision_api import state
from decision_api.endpoints import router
from decision_api.middleware import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(service_name="decision-api", log_level=settings.log_level)
    state.redis = aioredis.from_url(settings.redis_url)
    state.pg_pool = await asyncpg.create_pool(settings.postgres_dsn)
    state.health_checker = HealthChecker(
        redis=state.redis, pg_pool=state.pg_pool, service_name="decision-api"
    )
    get_logger().info("decision-api started")
    yield
    await state.pg_pool.close()
    await state.redis.aclose()


app = FastAPI(title="Decision API", version="0.1.0", lifespan=lifespan)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
app.add_middleware(RequestIdMiddleware)
app.include_router(router)


@app.get("/health")
async def health():
    return await state.health_checker.check()
