"""Publishes validated transactions to Redis Streams."""
from shared.models import Transaction
from shared.streams import StreamPublisher

STREAM_NAME = "stream:raw_transactions"


class TransactionPublisher:
    def __init__(self, stream_publisher: StreamPublisher):
        self._publisher = stream_publisher

    async def publish(self, txn: Transaction) -> bytes:
        data = {
            "txn_id": str(txn.txn_id),
            "user_id": txn.user_id,
            "amount": str(txn.amount),
            "currency": txn.currency,
            "merchant_id": txn.merchant_id,
            "mcc": txn.mcc,
            "timestamp": txn.timestamp.isoformat(),
            "latitude": str(txn.latitude),
            "longitude": str(txn.longitude),
            "device_fingerprint": txn.device_fingerprint,
            "ip_address": txn.ip_address,
        }
        return await self._publisher.publish(STREAM_NAME, data)
