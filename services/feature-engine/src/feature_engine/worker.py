"""Stream consumer worker for feature extraction pipeline."""

import json
import logging

from shared.feature_store import RedisFeatureStore
from shared.streams import RedisStreamConsumer, StreamPublisher

from feature_engine.orchestrator import FeatureOrchestrator

logger = logging.getLogger(__name__)

ENRICHED_STREAM = "stream:enriched_transactions"


async def process_message(
    msg_id: bytes,
    data: dict,
    orchestrator: FeatureOrchestrator,
    feature_store: RedisFeatureStore,
    publisher: StreamPublisher,
    consumer: RedisStreamConsumer,
) -> None:
    """Process a single raw transaction message from the stream."""
    # Decode bytes keys/values if needed
    decoded = {}
    for k, v in data.items():
        key = k.decode() if isinstance(k, bytes) else k
        val = v.decode() if isinstance(v, bytes) else v
        decoded[key] = val

    txn_id = decoded["txn_id"]
    user_id = decoded["user_id"]

    logger.info("Processing transaction %s for user %s", txn_id, user_id)

    features = await orchestrator.compute_all(
        txn_id=txn_id,
        user_id=user_id,
        amount=float(decoded["amount"]),
        merchant_id=decoded["merchant_id"],
        mcc=decoded["mcc"],
        timestamp=decoded["timestamp"],
        latitude=float(decoded["latitude"]),
        longitude=float(decoded["longitude"]),
        device_fingerprint=decoded["device_fingerprint"],
        ip_address=decoded["ip_address"],
    )

    # Store features as string values in Redis hash
    feature_dict = {k: str(v) for k, v in features.model_dump().items()}
    await feature_store.store_features(features.txn_id, feature_dict)

    # Publish enriched transaction
    enriched = dict(decoded)
    enriched["features_json"] = json.dumps(feature_dict)
    await publisher.publish(ENRICHED_STREAM, enriched)

    # Acknowledge the message
    await consumer.ack(msg_id)

    logger.info("Completed processing transaction %s", txn_id)


async def run_worker(
    redis_client,
    orchestrator: FeatureOrchestrator,
    feature_store: RedisFeatureStore,
    publisher: StreamPublisher,
) -> None:
    """Main consumer loop: read from stream:raw_transactions and process."""
    consumer = RedisStreamConsumer(
        redis_client,
        stream="stream:raw_transactions",
        group="feature-engine",
        consumer_name="worker-1",
    )
    await consumer.ensure_group()

    logger.info("Feature engine worker started, listening on stream:raw_transactions")

    while True:
        messages = await consumer.read(count=10, block=5000)
        for msg_id, data in messages:
            try:
                await process_message(
                    msg_id, data, orchestrator, feature_store, publisher, consumer
                )
            except Exception:
                logger.exception("Failed to process message %s", msg_id)
