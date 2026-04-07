"""Stream Ingester FastAPI application."""
from contextlib import asynccontextmanager
from typing import Optional

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from shared.config import get_settings
from shared.health import HealthChecker
from shared.middleware import RequestIdMiddleware
from shared.models import Transaction
from shared.streams import RedisStreamPublisher
from stream_ingester.publisher import TransactionPublisher

_publisher: Optional[TransactionPublisher] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _publisher
    settings = get_settings()
    redis_client = redis.from_url(settings.redis_url)
    stream_pub = RedisStreamPublisher(redis_client)
    _publisher = TransactionPublisher(stream_pub)
    app.state.health_checker = HealthChecker(
        redis=redis_client, service_name="stream-ingester"
    )
    yield
    await redis_client.aclose()


app = FastAPI(title="Stream Ingester", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestIdMiddleware)


@app.get("/health")
async def health():
    return await app.state.health_checker.check()


@app.post("/transactions", status_code=202)
async def ingest_transaction(txn: Transaction):
    await _publisher.publish(txn)
    return JSONResponse(
        status_code=202,
        content={"txn_id": str(txn.txn_id), "status": "accepted"},
    )
