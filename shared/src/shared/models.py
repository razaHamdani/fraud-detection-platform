"""Pydantic models for the fraud detection platform."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DecisionEnum(str, Enum):
    """Possible fraud decision outcomes."""

    APPROVE = "APPROVE"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


class Transaction(BaseModel):
    """Incoming payment transaction."""

    txn_id: UUID = Field(default_factory=uuid4)
    user_id: str
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    merchant_id: str
    mcc: str
    timestamp: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    device_fingerprint: str
    ip_address: str


class ScoreBreakdown(BaseModel):
    """Individual score component in a risk decision."""

    category: str
    sub_score: float = Field(ge=0, le=1)
    weight: float = Field(ge=0, le=1)
    contribution: float


class Decision(BaseModel):
    """Risk scoring decision for a transaction."""

    txn_id: UUID
    risk_score: float = Field(ge=0, le=1)
    decision: DecisionEnum
    breakdown: list[ScoreBreakdown]
    rules_triggered: list[str]
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )


class Chargeback(BaseModel):
    """Chargeback report linked to a transaction."""

    chargeback_id: UUID = Field(default_factory=uuid4)
    txn_id: UUID
    reason: str
    reported_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    processed_at: Optional[datetime] = None


class FeatureSet(BaseModel):
    """Computed feature vector for a transaction."""

    txn_id: UUID
    txn_count_5min: int
    txn_count_1hr: int
    txn_amount_sum_1hr: float
    unique_merchants_1hr: int
    geo_distance_km: float
    geo_velocity_kmh: float
    country_mismatch: bool
    shared_device_count: int
    shared_ip_count: int
    card_device_ratio: float
    graph_risk_cluster: float
    amount_zscore: float
    is_high_risk_mcc: bool
    is_first_transaction: bool
    time_of_day_risk: float


class Rule(BaseModel):
    """Configurable fraud detection rule."""

    rule_id: UUID = Field(default_factory=uuid4)
    name: str
    condition_json: dict
    action: DecisionEnum
    priority: int
    active: bool


class ScoringWeights(BaseModel):
    """Weights for the risk scoring model components."""

    velocity: float = Field(default=0.3, ge=0, le=1)
    geo: float = Field(default=0.2, ge=0, le=1)
    device: float = Field(default=0.3, ge=0, le=1)
    graph: float = Field(default=0.2, ge=0, le=1)
