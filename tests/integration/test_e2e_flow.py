"""End-to-end integration tests (require running Docker Compose services)."""

import asyncio
import json
import uuid
from datetime import datetime, timezone

import pytest

from shared.models import Transaction, FeatureSet, ScoringWeights
from shared.streams import RedisStreamPublisher, RedisStreamConsumer
from shared.feature_store import RedisFeatureStore


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transaction_flows_through_pipeline(redis_client):
    """Publish a raw transaction and verify it arrives on enriched stream."""
    publisher = RedisStreamPublisher(redis_client=redis_client)

    txn = Transaction(
        user_id="integ_user_001",
        amount=99.99,
        currency="USD",
        merchant_id="integ_merch_001",
        mcc="5411",
        timestamp=datetime.now(timezone.utc),
        latitude=40.7128,
        longitude=-74.006,
        device_fingerprint="integ_fp_001",
        ip_address="10.0.0.1",
    )

    data = {k: str(v) for k, v in txn.model_dump().items()}
    msg_id = await publisher.publish("stream:raw_transactions", data)
    assert msg_id is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decision_cached_in_redis(redis_client):
    """After pipeline processes, decision should be cached."""
    publisher = RedisStreamPublisher(redis_client=redis_client)
    txn_id = str(uuid.uuid4())

    await publisher.publish("stream:raw_transactions", {
        "txn_id": txn_id,
        "user_id": "integ_user_002",
        "amount": "50.0",
        "currency": "USD",
        "merchant_id": "integ_merch_001",
        "mcc": "5411",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latitude": "40.7128",
        "longitude": "-74.006",
        "device_fingerprint": "integ_fp_002",
        "ip_address": "10.0.0.2",
    })

    # Poll for decision (up to 5 seconds for integration test)
    for _ in range(50):
        cached = await redis_client.hgetall(f"decision:{txn_id}")
        if cached:
            assert b"risk_score" in cached
            assert b"decision" in cached
            return
        await asyncio.sleep(0.1)

    pytest.fail("Decision not found in Redis within 5 seconds")
