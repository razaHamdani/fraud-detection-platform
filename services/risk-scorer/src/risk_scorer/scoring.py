"""Weighted risk scoring formula."""

from shared.models import Decision, DecisionEnum, FeatureSet, ScoreBreakdown, ScoringWeights


def velocity_score(f: FeatureSet) -> float:
    """Map velocity features to 0.0-1.0 risk score."""
    score = 0.0
    score += min(f.txn_count_5min / 10.0, 1.0) * 0.3
    score += min(f.txn_count_1hr / 30.0, 1.0) * 0.3
    score += min(f.txn_amount_sum_1hr / 10000.0, 1.0) * 0.2
    score += (1.0 if f.unique_merchants_1hr <= 1 and f.txn_count_1hr > 5 else 0.0) * 0.2
    return min(score, 1.0)


def geo_score(f: FeatureSet) -> float:
    """Map geo features to 0.0-1.0 risk score."""
    score = 0.0
    score += min(f.geo_distance_km / 5000.0, 1.0) * 0.3
    score += (1.0 if f.geo_velocity_kmh > 900 else min(f.geo_velocity_kmh / 900.0, 1.0)) * 0.4
    score += (0.5 if f.country_mismatch else 0.0) * 0.3
    return min(score, 1.0)


def device_score(f: FeatureSet) -> float:
    """Map device features to 0.0-1.0 risk score."""
    score = 0.0
    score += min(f.shared_device_count / 10.0, 1.0) * 0.4
    score += min(f.shared_ip_count / 10.0, 1.0) * 0.3
    score += min(f.card_device_ratio / 5.0, 1.0) * 0.3
    return min(score, 1.0)


def graph_score(f: FeatureSet) -> float:
    """Map graph features to 0.0-1.0 risk score."""
    score = 0.0
    score += min(f.graph_risk_cluster, 1.0) * 0.6
    score += min(f.shared_device_count / 5.0, 1.0) * 0.2
    score += min(f.shared_ip_count / 5.0, 1.0) * 0.2
    return min(score, 1.0)


def _decide(score: float) -> DecisionEnum:
    """Map a final risk score to a decision."""
    if score < 0.3:
        return DecisionEnum.APPROVE
    elif score < 0.7:
        return DecisionEnum.HOLD
    return DecisionEnum.BLOCK


def compute_risk_score(features: FeatureSet, weights: ScoringWeights) -> Decision:
    """Compute weighted risk score from feature set and return a Decision."""
    v = velocity_score(features)
    g = geo_score(features)
    d = device_score(features)
    gr = graph_score(features)

    weighted = (
        v * weights.velocity
        + g * weights.geo
        + d * weights.device
        + gr * weights.graph
    )
    final_score = min(max(weighted, 0.0), 1.0)

    breakdown = [
        ScoreBreakdown(category="velocity", sub_score=round(v, 4), weight=weights.velocity, contribution=round(v * weights.velocity, 4)),
        ScoreBreakdown(category="geo", sub_score=round(g, 4), weight=weights.geo, contribution=round(g * weights.geo, 4)),
        ScoreBreakdown(category="device", sub_score=round(d, 4), weight=weights.device, contribution=round(d * weights.device, 4)),
        ScoreBreakdown(category="graph", sub_score=round(gr, 4), weight=weights.graph, contribution=round(gr * weights.graph, 4)),
    ]

    return Decision(
        txn_id=features.txn_id,
        risk_score=round(final_score, 4),
        decision=_decide(final_score),
        breakdown=breakdown,
        rules_triggered=[],
    )
