"""Tests for shared.models — Pydantic models for the fraud detection platform."""

from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from shared.models import (
    Chargeback,
    Decision,
    DecisionEnum,
    FeatureSet,
    Rule,
    ScoreBreakdown,
    ScoringWeights,
    Transaction,
)


# --- Transaction ---


class TestTransaction:
    def test_valid_creation(self):
        txn = Transaction(
            user_id="u-123",
            amount=99.99,
            currency="USD",
            merchant_id="m-456",
            mcc="5411",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            latitude=40.7128,
            longitude=-74.0060,
            device_fingerprint="fp-abc",
            ip_address="192.168.1.1",
        )
        assert isinstance(txn.txn_id, UUID)
        assert txn.user_id == "u-123"
        assert txn.amount == 99.99
        assert txn.currency == "USD"

    def test_uuid_auto_generated(self):
        txn1 = Transaction(
            user_id="u-1",
            amount=1.0,
            currency="USD",
            merchant_id="m-1",
            mcc="5411",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            latitude=0.0,
            longitude=0.0,
            device_fingerprint="fp",
            ip_address="1.2.3.4",
        )
        txn2 = Transaction(
            user_id="u-1",
            amount=1.0,
            currency="USD",
            merchant_id="m-1",
            mcc="5411",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            latitude=0.0,
            longitude=0.0,
            device_fingerprint="fp",
            ip_address="1.2.3.4",
        )
        assert txn1.txn_id != txn2.txn_id

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            Transaction(
                user_id="u-1",
                amount=-10.0,
                currency="USD",
                merchant_id="m-1",
                mcc="5411",
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                latitude=0.0,
                longitude=0.0,
                device_fingerprint="fp",
                ip_address="1.2.3.4",
            )

    def test_zero_amount_rejected(self):
        with pytest.raises(ValidationError):
            Transaction(
                user_id="u-1",
                amount=0.0,
                currency="USD",
                merchant_id="m-1",
                mcc="5411",
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                latitude=0.0,
                longitude=0.0,
                device_fingerprint="fp",
                ip_address="1.2.3.4",
            )

    def test_currency_must_be_3_chars(self):
        with pytest.raises(ValidationError):
            Transaction(
                user_id="u-1",
                amount=10.0,
                currency="US",
                merchant_id="m-1",
                mcc="5411",
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                latitude=0.0,
                longitude=0.0,
                device_fingerprint="fp",
                ip_address="1.2.3.4",
            )

    def test_latitude_out_of_range(self):
        with pytest.raises(ValidationError):
            Transaction(
                user_id="u-1",
                amount=10.0,
                currency="USD",
                merchant_id="m-1",
                mcc="5411",
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                latitude=91.0,
                longitude=0.0,
                device_fingerprint="fp",
                ip_address="1.2.3.4",
            )

    def test_longitude_out_of_range(self):
        with pytest.raises(ValidationError):
            Transaction(
                user_id="u-1",
                amount=10.0,
                currency="USD",
                merchant_id="m-1",
                mcc="5411",
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                latitude=0.0,
                longitude=181.0,
                device_fingerprint="fp",
                ip_address="1.2.3.4",
            )


# --- ScoreBreakdown ---


class TestScoreBreakdown:
    def test_valid(self):
        sb = ScoreBreakdown(
            category="velocity", sub_score=0.8, weight=0.3, contribution=0.24
        )
        assert sb.category == "velocity"

    def test_invalid_score_above_1(self):
        with pytest.raises(ValidationError):
            ScoreBreakdown(
                category="velocity", sub_score=1.5, weight=0.3, contribution=0.45
            )

    def test_invalid_weight_below_0(self):
        with pytest.raises(ValidationError):
            ScoreBreakdown(
                category="velocity", sub_score=0.5, weight=-0.1, contribution=-0.05
            )


# --- Decision ---


class TestDecision:
    def test_valid_creation(self):
        d = Decision(
            txn_id=UUID("12345678-1234-5678-1234-567812345678"),
            risk_score=0.85,
            decision=DecisionEnum.BLOCK,
            breakdown=[],
            rules_triggered=["high_velocity"],
        )
        assert d.decision == DecisionEnum.BLOCK
        assert isinstance(d.created_at, datetime)

    def test_invalid_risk_score(self):
        with pytest.raises(ValidationError):
            Decision(
                txn_id=UUID("12345678-1234-5678-1234-567812345678"),
                risk_score=1.5,
                decision=DecisionEnum.APPROVE,
                breakdown=[],
                rules_triggered=[],
            )


# --- Chargeback ---


class TestChargeback:
    def test_defaults(self):
        cb = Chargeback(
            txn_id=UUID("12345678-1234-5678-1234-567812345678"),
            reason="unauthorized",
        )
        assert isinstance(cb.chargeback_id, UUID)
        assert isinstance(cb.reported_at, datetime)
        assert cb.processed_at is None

    def test_with_processed_at(self):
        now = datetime.now(tz=timezone.utc)
        cb = Chargeback(
            txn_id=UUID("12345678-1234-5678-1234-567812345678"),
            reason="unauthorized",
            processed_at=now,
        )
        assert cb.processed_at == now


# --- FeatureSet ---


class TestFeatureSet:
    def test_valid_creation(self):
        fs = FeatureSet(
            txn_id=UUID("12345678-1234-5678-1234-567812345678"),
            txn_count_5min=3,
            txn_count_1hr=10,
            txn_amount_sum_1hr=500.0,
            unique_merchants_1hr=4,
            geo_distance_km=15.2,
            geo_velocity_kmh=120.0,
            country_mismatch=False,
            shared_device_count=1,
            shared_ip_count=2,
            card_device_ratio=1.5,
            graph_risk_cluster=0.3,
            amount_zscore=2.1,
            is_high_risk_mcc=False,
            is_first_transaction=True,
            time_of_day_risk=0.7,
        )
        assert fs.txn_count_5min == 3
        assert fs.is_first_transaction is True


# --- Rule ---


class TestRule:
    def test_valid_creation(self):
        r = Rule(
            name="high_velocity",
            condition_json={"field": "txn_count_5min", "op": ">", "value": 5},
            action=DecisionEnum.HOLD,
            priority=1,
            active=True,
        )
        assert isinstance(r.rule_id, UUID)
        assert r.name == "high_velocity"


# --- ScoringWeights ---


class TestScoringWeights:
    def test_defaults(self):
        sw = ScoringWeights()
        assert sw.velocity == 0.3
        assert sw.geo == 0.2
        assert sw.device == 0.3
        assert sw.graph == 0.2

    def test_invalid_weight(self):
        with pytest.raises(ValidationError):
            ScoringWeights(velocity=1.5)

    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValidationError, match="Weights must sum to 1.0"):
            ScoringWeights(velocity=0.5, geo=0.5, device=0.5, graph=0.5)

    def test_custom_weights_summing_to_one(self):
        sw = ScoringWeights(velocity=0.4, geo=0.1, device=0.4, graph=0.1)
        assert sw.velocity == 0.4
