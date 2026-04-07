"""Feature Engine service with FastAPI and background stream worker."""

import asyncio
import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from neo4j import GraphDatabase

from shared.config import get_settings
from shared.feature_store import RedisFeatureStore
from shared.health import HealthChecker
from shared.middleware import RequestIdMiddleware
from shared.streams import RedisStreamPublisher

from feature_engine.geo import GeoCalculator
from feature_engine.graph import GraphCalculator
from feature_engine.orchestrator import FeatureOrchestrator
from feature_engine.velocity import VelocityCalculator
from feature_engine.worker import run_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Initialize Redis
    redis = aioredis.from_url(settings.redis_url, decode_responses=False)
    feature_store = RedisFeatureStore(redis)
    publisher = RedisStreamPublisher(redis)

    # Initialize Neo4j driver
    neo4j_driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    # Initialize calculators
    velocity = VelocityCalculator(feature_store)
    geo = GeoCalculator(redis)
    graph = GraphCalculator(neo4j_driver)

    # Assemble orchestrator
    orchestrator = FeatureOrchestrator(velocity, geo, graph)

    # Start background worker
    worker_task = asyncio.create_task(
        run_worker(redis, orchestrator, feature_store, publisher)
    )
    app.state.health_checker = HealthChecker(
        redis=redis, neo4j_driver=neo4j_driver, service_name="feature-engine"
    )
    logger.info("Feature engine service started")

    yield

    # Shutdown
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    neo4j_driver.close()
    await redis.aclose()
    logger.info("Feature engine service stopped")


app = FastAPI(title="Feature Engine", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestIdMiddleware)


@app.get("/health")
async def health():
    return await app.state.health_checker.check()
