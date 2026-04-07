"""Post-score rule engine with configurable rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from shared.models import Decision, DecisionEnum, FeatureSet


@dataclass
class Rule:
    name: str
    condition: Callable[[FeatureSet], bool]
    action: DecisionEnum
    description: str
    priority: int = 0


DEFAULT_RULES = [
    Rule(
        name="geo_velocity_kmh > 900",
        condition=lambda f: f.geo_velocity_kmh > 900,
        action=DecisionEnum.BLOCK,
        description="Impossible travel detection",
        priority=100,
    ),
    Rule(
        name="high_amount_first_txn",
        condition=lambda f: f.is_first_transaction and f.amount_zscore > 5,
        action=DecisionEnum.BLOCK,
        description="High amount on first transaction",
        priority=90,
    ),
    Rule(
        name="shared_device_count > 5",
        condition=lambda f: f.shared_device_count > 5,
        action=DecisionEnum.HOLD,
        description="Too many users sharing device",
        priority=80,
    ),
]


def apply_rules(
    decision: Decision,
    features: FeatureSet,
    rules: list[Rule],
) -> Decision:
    """Apply rules in priority order. BLOCK overrides HOLD overrides APPROVE."""
    triggered: list[str] = []
    final_action = decision.decision

    sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)

    for rule in sorted_rules:
        if rule.condition(features):
            triggered.append(rule.name)
            if rule.action == DecisionEnum.BLOCK:
                final_action = DecisionEnum.BLOCK
            elif rule.action == DecisionEnum.HOLD and final_action != DecisionEnum.BLOCK:
                final_action = DecisionEnum.HOLD

    return Decision(
        txn_id=decision.txn_id,
        risk_score=decision.risk_score,
        decision=final_action,
        breakdown=decision.breakdown,
        rules_triggered=triggered,
        created_at=decision.created_at,
    )
