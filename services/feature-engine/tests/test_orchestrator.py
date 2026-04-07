"""Tests for the feature orchestrator."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from feature_engine.orchestrator import FeatureOrchestrator


@pytest.fixture
def velocity_calculator():
    calc = AsyncMock()
    calc.compute = AsyncMock(
        return_value={
            "txn_count_5min": 2,
            "txn_count_1hr": 5,
            "unique_merchants_1hr": 3,
            "txn_amount_sum_1hr": 250.0,
        }
    )
    return calc


@pytest.fixture
def geo_calculator():
    calc = AsyncMock()
    calc.compute = AsyncMock(
        return_value={
            "geo_distance_km": 100.0,
            "geo_velocity_kmh": 200.0,
            "country_mismatch": False,
        }
    )
    return calc


@pytest.fixture
def graph_calculator():
    calc = AsyncMock()
    calc.compute = AsyncMock(
        return_value={
            "shared_device_count": 1,
            "shared_ip_count": 0,
            "card_device_ratio": 0.5,
            "graph_risk_cluster": False,
        }
    )
    return calc


@pytest.fixture
def orchestrator(velocity_calculator, geo_calculator, graph_calculator):
    return FeatureOrchestrator(velocity_calculator, geo_calculator, graph_calculator)


@pytest.fixture
def txn_kwargs():
    return {
        "txn_id": str(uuid4()),
        "user_id": "user-1",
        "amount": 150.0,
        "merchant_id": "merchant-1",
        "mcc": "5411",
        "timestamp": "2024-01-01T14:00:00+00:00",
        "latitude": 40.7128,
        "longitude": -74.006,
        "device_fingerprint": "fp-abc",
        "ip_address": "1.2.3.4",
    }


@pytest.mark.asyncio
async def test_compute_all_returns_feature_set(orchestrator, txn_kwargs):
    result = await orchestrator.compute_all(**txn_kwargs)

    assert result.txn_count_5min == 2
    assert result.txn_count_1hr == 5
    assert result.unique_merchants_1hr == 3
    assert result.txn_amount_sum_1hr == 250.0
    assert result.geo_distance_km == 100.0
    assert result.geo_velocity_kmh == 200.0
    assert result.country_mismatch is False
    assert result.shared_device_count == 1
    assert result.shared_ip_count == 0
    assert result.card_device_ratio == 0.5
    assert result.graph_risk_cluster == 0.0


@pytest.mark.asyncio
async def test_compute_all_calculates_amount_zscore(orchestrator, txn_kwargs):
    txn_kwargs["amount"] = 180.0
    result = await orchestrator.compute_all(**txn_kwargs)
    # (180 - 100) / 80 = 1.0
    assert result.amount_zscore == 1.0


@pytest.mark.asyncio
async def test_compute_all_calculates_time_of_day_risk(orchestrator, txn_kwargs):
    txn_kwargs["timestamp"] = "2024-01-01T03:00:00+00:00"
    result = await orchestrator.compute_all(**txn_kwargs)
    assert result.time_of_day_risk == 0.8


@pytest.mark.asyncio
async def test_compute_all_detects_high_risk_mcc(orchestrator, txn_kwargs):
    txn_kwargs["mcc"] = "7995"
    result = await orchestrator.compute_all(**txn_kwargs)
    assert result.is_high_risk_mcc is True


@pytest.mark.asyncio
async def test_compute_all_normal_mcc(orchestrator, txn_kwargs):
    result = await orchestrator.compute_all(**txn_kwargs)
    assert result.is_high_risk_mcc is False


@pytest.mark.asyncio
async def test_is_first_transaction_when_count_is_1(
    velocity_calculator, geo_calculator, graph_calculator, txn_kwargs
):
    velocity_calculator.compute = AsyncMock(
        return_value={
            "txn_count_5min": 1,
            "txn_count_1hr": 1,
            "unique_merchants_1hr": 1,
            "txn_amount_sum_1hr": 50.0,
        }
    )
    orchestrator = FeatureOrchestrator(
        velocity_calculator, geo_calculator, graph_calculator
    )

    result = await orchestrator.compute_all(**txn_kwargs)
    assert result.is_first_transaction is True


@pytest.mark.asyncio
async def test_is_not_first_transaction_when_count_gt_1(orchestrator, txn_kwargs):
    # Default velocity mock returns txn_count_1hr=5
    result = await orchestrator.compute_all(**txn_kwargs)
    assert result.is_first_transaction is False


@pytest.mark.asyncio
async def test_parallel_execution(
    orchestrator, velocity_calculator, geo_calculator, graph_calculator, txn_kwargs
):
    """Verify all calculators are called."""
    await orchestrator.compute_all(**txn_kwargs)

    velocity_calculator.compute.assert_called_once()
    geo_calculator.compute.assert_called_once()
    graph_calculator.compute.assert_called_once()
