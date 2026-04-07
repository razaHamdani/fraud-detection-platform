"""Tests for velocity feature calculator."""

from unittest.mock import AsyncMock

import pytest

from feature_engine.velocity import VelocityCalculator


@pytest.fixture
def feature_store():
    store = AsyncMock()
    store.record_and_count = AsyncMock(return_value=3)
    store.record_sum = AsyncMock(return_value=150.0)
    return store


@pytest.fixture
def calculator(feature_store):
    return VelocityCalculator(feature_store)


@pytest.mark.asyncio
async def test_compute_returns_all_keys(calculator):
    result = await calculator.compute(
        user_id="user-1",
        txn_id="txn-abc",
        amount=50.0,
        merchant_id="merchant-1",
    )

    assert "txn_count_5min" in result
    assert "txn_count_1hr" in result
    assert "unique_merchants_1hr" in result
    assert "txn_amount_sum_1hr" in result


@pytest.mark.asyncio
async def test_compute_calls_record_and_count_for_txn_counts(calculator, feature_store):
    await calculator.compute(
        user_id="user-1",
        txn_id="txn-abc",
        amount=50.0,
        merchant_id="merchant-1",
    )

    calls = feature_store.record_and_count.call_args_list
    assert len(calls) == 3

    # 5-minute window
    assert calls[0].kwargs["key"] == "velocity:txn_count_5min:user-1"
    assert calls[0].kwargs["window_seconds"] == 300
    assert calls[0].kwargs["member"] == "txn-abc"

    # 1-hour window
    assert calls[1].kwargs["key"] == "velocity:txn_count_1hr:user-1"
    assert calls[1].kwargs["window_seconds"] == 3600
    assert calls[1].kwargs["member"] == "txn-abc"

    # unique merchants
    assert calls[2].kwargs["key"] == "velocity:unique_merchants_1hr:user-1"
    assert calls[2].kwargs["window_seconds"] == 3600
    assert calls[2].kwargs["member"] == "merchant-1"


@pytest.mark.asyncio
async def test_compute_calls_record_sum_for_amount(calculator, feature_store):
    await calculator.compute(
        user_id="user-1",
        txn_id="txn-abc",
        amount=75.5,
        merchant_id="merchant-1",
    )

    feature_store.record_sum.assert_called_once_with(
        key="velocity:txn_amount_sum_1hr:user-1",
        window_seconds=3600,
        member="txn-abc",
        amount=75.5,
    )


@pytest.mark.asyncio
async def test_compute_returns_correct_values(feature_store):
    feature_store.record_and_count = AsyncMock(side_effect=[2, 5, 3])
    feature_store.record_sum = AsyncMock(return_value=250.0)
    calculator = VelocityCalculator(feature_store)

    result = await calculator.compute(
        user_id="user-1",
        txn_id="txn-abc",
        amount=100.0,
        merchant_id="merchant-1",
    )

    assert result["txn_count_5min"] == 2
    assert result["txn_count_1hr"] == 5
    assert result["unique_merchants_1hr"] == 3
    assert result["txn_amount_sum_1hr"] == 250.0
