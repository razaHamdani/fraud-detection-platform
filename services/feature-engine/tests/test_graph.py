"""Tests for Neo4j graph feature calculator."""

from unittest.mock import MagicMock, patch

import pytest

from feature_engine.graph import SAFE_DEFAULTS, GraphCalculator


@pytest.fixture
def mock_record():
    record = MagicMock()
    record.__getitem__ = MagicMock(
        side_effect=lambda key: {
            "shared_device_count": 2,
            "shared_ip_count": 1,
            "card_device_ratio": 0.5,
        }[key]
    )
    return record


@pytest.fixture
def mock_driver(mock_record):
    driver = MagicMock()
    session = MagicMock()
    result = MagicMock()
    result.single.return_value = mock_record

    session.run = MagicMock(side_effect=[MagicMock(), result])
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    driver.session.return_value = session
    return driver


@pytest.fixture
def calculator(mock_driver):
    return GraphCalculator(mock_driver)


@pytest.mark.asyncio
async def test_compute_returns_features(calculator):
    result = await calculator.compute(
        user_id="user-1",
        device_fingerprint="fp-abc",
        ip_address="1.2.3.4",
        merchant_id="merchant-1",
    )

    assert result["shared_device_count"] == 2
    assert result["shared_ip_count"] == 1
    assert result["card_device_ratio"] == 0.5
    assert result["graph_risk_cluster"] is False


@pytest.mark.asyncio
async def test_compute_calls_upsert_and_feature_queries(calculator, mock_driver):
    await calculator.compute(
        user_id="user-1",
        device_fingerprint="fp-abc",
        ip_address="1.2.3.4",
        merchant_id="merchant-1",
    )

    session = mock_driver.session.return_value.__enter__.return_value
    assert session.run.call_count == 2


@pytest.mark.asyncio
async def test_graceful_degradation_on_connection_error():
    driver = MagicMock()
    driver.session.side_effect = ConnectionError("refused")
    calculator = GraphCalculator(driver)

    result = await calculator.compute(
        user_id="user-1",
        device_fingerprint="fp-abc",
        ip_address="1.2.3.4",
        merchant_id="merchant-1",
    )

    assert result == SAFE_DEFAULTS


@pytest.mark.asyncio
async def test_graceful_degradation_on_timeout():
    driver = MagicMock()
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    import time

    def slow_run(*args, **kwargs):
        time.sleep(10)

    session.run = slow_run
    driver.session.return_value = session

    calculator = GraphCalculator(driver)

    # Patch timeout to be very short for test
    with patch("feature_engine.graph.TIMEOUT_SECONDS", 0.1):
        result = await calculator.compute(
            user_id="user-1",
            device_fingerprint="fp-abc",
            ip_address="1.2.3.4",
            merchant_id="merchant-1",
        )

    assert result == SAFE_DEFAULTS


@pytest.mark.asyncio
async def test_graceful_degradation_on_runtime_error():
    driver = MagicMock()
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    session.run.side_effect = RuntimeError("unexpected")
    driver.session.return_value = session
    calculator = GraphCalculator(driver)

    result = await calculator.compute(
        user_id="user-1",
        device_fingerprint="fp-abc",
        ip_address="1.2.3.4",
        merchant_id="merchant-1",
    )

    assert result == SAFE_DEFAULTS
