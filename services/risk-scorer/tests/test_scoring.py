import pytest
from shared.models import FeatureSet, ScoringWeights
import uuid


@pytest.fixture
def low_risk_features():
    return FeatureSet(
        txn_id=uuid.uuid4(),
        txn_count_5min=1, txn_count_1hr=3, txn_amount_sum_1hr=150.0,
        unique_merchants_1hr=2,
        geo_distance_km=1.0, geo_velocity_kmh=5.0, country_mismatch=False,
        shared_device_count=1, shared_ip_count=1, card_device_ratio=1.0,
        graph_risk_cluster=False,
        amount_zscore=0.2, is_high_risk_mcc=False,
        is_first_transaction=False, time_of_day_risk=0.1,
    )


@pytest.fixture
def high_risk_features():
    return FeatureSet(
        txn_id=uuid.uuid4(),
        txn_count_5min=15, txn_count_1hr=50, txn_amount_sum_1hr=25000.0,
        unique_merchants_1hr=1,
        geo_distance_km=5000.0, geo_velocity_kmh=5000.0, country_mismatch=True,
        shared_device_count=10, shared_ip_count=8, card_device_ratio=5.0,
        graph_risk_cluster=True,
        amount_zscore=8.0, is_high_risk_mcc=True,
        is_first_transaction=True, time_of_day_risk=0.8,
    )


def test_velocity_sub_score_low(low_risk_features):
    from risk_scorer.scoring import velocity_score
    score = velocity_score(low_risk_features)
    assert 0.0 <= score <= 0.3


def test_velocity_sub_score_high(high_risk_features):
    from risk_scorer.scoring import velocity_score
    score = velocity_score(high_risk_features)
    assert score > 0.7


def test_compute_risk_score_low(low_risk_features):
    from risk_scorer.scoring import compute_risk_score
    weights = ScoringWeights()
    result = compute_risk_score(low_risk_features, weights)
    assert result.risk_score < 0.3
    assert result.decision.value == "APPROVE"


def test_compute_risk_score_high(high_risk_features):
    from risk_scorer.scoring import compute_risk_score
    weights = ScoringWeights()
    result = compute_risk_score(high_risk_features, weights)
    assert result.risk_score > 0.7
    assert result.decision.value == "BLOCK"


def test_score_breakdown_has_4_categories(low_risk_features):
    from risk_scorer.scoring import compute_risk_score
    weights = ScoringWeights()
    result = compute_risk_score(low_risk_features, weights)
    assert len(result.breakdown) == 4
    categories = {b.category for b in result.breakdown}
    assert categories == {"velocity", "geo", "device", "graph"}
