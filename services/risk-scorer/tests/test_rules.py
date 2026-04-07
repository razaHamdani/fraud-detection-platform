import uuid
import pytest
from shared.models import Decision, DecisionEnum, FeatureSet, ScoreBreakdown


@pytest.fixture
def base_decision():
    return Decision(
        txn_id=uuid.uuid4(),
        risk_score=0.15,
        decision=DecisionEnum.APPROVE,
        breakdown=[
            ScoreBreakdown(category="velocity", sub_score=0.1, weight=0.3, contribution=0.03),
        ],
        rules_triggered=[],
    )


@pytest.fixture
def impossible_travel_features():
    return FeatureSet(
        txn_id=uuid.uuid4(),
        txn_count_5min=0, txn_count_1hr=0, txn_amount_sum_1hr=0,
        unique_merchants_1hr=0, geo_distance_km=0, geo_velocity_kmh=1500.0,
        country_mismatch=False, shared_device_count=0, shared_ip_count=0,
        card_device_ratio=1.0, graph_risk_cluster=0, amount_zscore=0,
        is_high_risk_mcc=False, is_first_transaction=False, time_of_day_risk=0,
    )


def test_impossible_travel_triggers_block(base_decision, impossible_travel_features):
    from risk_scorer.rules import apply_rules, DEFAULT_RULES
    result = apply_rules(base_decision, impossible_travel_features, DEFAULT_RULES)
    assert result.decision == DecisionEnum.BLOCK
    assert "geo_velocity_kmh > 900" in result.rules_triggered


def test_shared_devices_triggers_hold(base_decision):
    from risk_scorer.rules import apply_rules, DEFAULT_RULES
    features = FeatureSet(
        txn_id=base_decision.txn_id,
        txn_count_5min=0, txn_count_1hr=0, txn_amount_sum_1hr=0,
        unique_merchants_1hr=0, geo_distance_km=0, geo_velocity_kmh=0,
        country_mismatch=False, shared_device_count=8, shared_ip_count=0,
        card_device_ratio=1.0, graph_risk_cluster=0, amount_zscore=0,
        is_high_risk_mcc=False, is_first_transaction=False, time_of_day_risk=0,
    )
    result = apply_rules(base_decision, features, DEFAULT_RULES)
    assert result.decision == DecisionEnum.HOLD
    assert "shared_device_count > 5" in result.rules_triggered


def test_no_rules_triggered_keeps_original(base_decision):
    from risk_scorer.rules import apply_rules, DEFAULT_RULES
    features = FeatureSet(
        txn_id=base_decision.txn_id,
        txn_count_5min=0, txn_count_1hr=0, txn_amount_sum_1hr=0,
        unique_merchants_1hr=0, geo_distance_km=0, geo_velocity_kmh=0,
        country_mismatch=False, shared_device_count=0, shared_ip_count=0,
        card_device_ratio=1.0, graph_risk_cluster=0, amount_zscore=0,
        is_high_risk_mcc=False, is_first_transaction=False, time_of_day_risk=0,
    )
    result = apply_rules(base_decision, features, DEFAULT_RULES)
    assert result.decision == DecisionEnum.APPROVE
    assert result.rules_triggered == []
