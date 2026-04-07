"""Tests for TransactionPublisher."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from shared.models import Transaction
from stream_ingester.publisher import STREAM_NAME, TransactionPublisher


def _make_txn(**overrides) -> Transaction:
    defaults = {
        "txn_id": uuid4(),
        "user_id": "user-123",
        "amount": 99.99,
        "currency": "USD",
        "merchant_id": "merch-456",
        "mcc": "5411",
        "timestamp": datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        "latitude": 40.7128,
        "longitude": -74.0060,
        "device_fingerprint": "fp-abc",
        "ip_address": "192.168.1.1",
    }
    defaults.update(overrides)
    return Transaction(**defaults)


@pytest.mark.asyncio
async def test_publish_calls_stream_publisher_with_correct_stream():
    mock_publisher = AsyncMock()
    mock_publisher.publish.return_value = b"1234-0"
    publisher = TransactionPublisher(mock_publisher)
    txn = _make_txn()

    result = await publisher.publish(txn)

    mock_publisher.publish.assert_called_once()
    call_args = mock_publisher.publish.call_args
    assert call_args[0][0] == STREAM_NAME == "stream:raw_transactions"
    assert result == b"1234-0"


@pytest.mark.asyncio
async def test_publish_serializes_all_fields_as_strings():
    mock_publisher = AsyncMock()
    mock_publisher.publish.return_value = b"1234-0"
    publisher = TransactionPublisher(mock_publisher)
    txn = _make_txn()

    await publisher.publish(txn)

    data = mock_publisher.publish.call_args[0][1]
    for key, value in data.items():
        assert isinstance(value, str), f"Field '{key}' is {type(value)}, expected str"

    assert data["txn_id"] == str(txn.txn_id)
    assert data["user_id"] == txn.user_id
    assert data["amount"] == str(txn.amount)
    assert data["currency"] == txn.currency
    assert data["merchant_id"] == txn.merchant_id
    assert data["mcc"] == txn.mcc
    assert data["timestamp"] == txn.timestamp.isoformat()
    assert data["latitude"] == str(txn.latitude)
    assert data["longitude"] == str(txn.longitude)
    assert data["device_fingerprint"] == txn.device_fingerprint
    assert data["ip_address"] == txn.ip_address
