import uuid
from unittest.mock import AsyncMock

import pytest

from shared.models import Chargeback, ScoringWeights


@pytest.mark.asyncio
async def test_process_chargeback():
    from feedback_service.chargeback import ChargebackProcessor

    mock_pg = AsyncMock()
    mock_pg.execute = AsyncMock()
    mock_pg.fetchrow = AsyncMock(return_value={
        "breakdown_json": '[{"category":"velocity","sub_score":0.9,"weight":0.3,"contribution":0.27},'
                         '{"category":"geo","sub_score":0.1,"weight":0.2,"contribution":0.02},'
                         '{"category":"device","sub_score":0.1,"weight":0.3,"contribution":0.03},'
                         '{"category":"graph","sub_score":0.1,"weight":0.2,"contribution":0.02}]'
    })
    mock_pg.fetch = AsyncMock(return_value=[
        {"category": "velocity", "weight": 0.3},
        {"category": "geo", "weight": 0.2},
        {"category": "device", "weight": 0.3},
        {"category": "graph", "weight": 0.2},
    ])
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock()

    processor = ChargebackProcessor(pg_pool=mock_pg, redis=mock_redis)
    cb = Chargeback(txn_id=uuid.uuid4(), reason="unauthorized")
    result = await processor.process(cb)

    assert result is True
    mock_pg.execute.assert_called()


@pytest.mark.asyncio
async def test_weight_adjustment_ema():
    from feedback_service.chargeback import adjust_weights

    current = ScoringWeights(velocity=0.3, geo=0.2, device=0.3, graph=0.2)
    # If velocity had high sub_score in fraud case, its weight should increase
    breakdown = [
        {"category": "velocity", "sub_score": 0.9},
        {"category": "geo", "sub_score": 0.1},
        {"category": "device", "sub_score": 0.1},
        {"category": "graph", "sub_score": 0.1},
    ]
    new_weights = adjust_weights(current, breakdown, alpha=0.1)
    assert new_weights.velocity > current.velocity
    # Weights should still sum to ~1.0
    total = new_weights.velocity + new_weights.geo + new_weights.device + new_weights.graph
    assert abs(total - 1.0) < 0.01


@pytest.mark.asyncio
async def test_process_chargeback_no_decision():
    from feedback_service.chargeback import ChargebackProcessor

    mock_pg = AsyncMock()
    mock_pg.execute = AsyncMock()
    mock_pg.fetchrow = AsyncMock(return_value=None)
    mock_redis = AsyncMock()

    processor = ChargebackProcessor(pg_pool=mock_pg, redis=mock_redis)
    cb = Chargeback(txn_id=uuid.uuid4(), reason="unauthorized")
    result = await processor.process(cb)

    assert result is False
