"""Feature orchestrator that runs all calculators in parallel."""

import asyncio
from datetime import datetime
from uuid import UUID

from shared.models import FeatureSet

from feature_engine.geo import GeoCalculator
from feature_engine.graph import GraphCalculator
from feature_engine.transaction import (
    compute_amount_zscore,
    compute_time_of_day_risk,
    is_high_risk_mcc,
)
from feature_engine.velocity import VelocityCalculator

# Hardcoded baselines (to be replaced with learned values)
AMOUNT_MEAN = 100.0
AMOUNT_STDDEV = 80.0


class FeatureOrchestrator:
    """Orchestrate parallel feature computation across all calculators."""

    def __init__(
        self,
        velocity: VelocityCalculator,
        geo: GeoCalculator,
        graph: GraphCalculator,
    ) -> None:
        self._velocity = velocity
        self._geo = geo
        self._graph = graph

    async def compute_all(
        self,
        txn_id: str,
        user_id: str,
        amount: float,
        merchant_id: str,
        mcc: str,
        timestamp: str,
        latitude: float,
        longitude: float,
        device_fingerprint: str,
        ip_address: str,
    ) -> FeatureSet:
        """Run all feature calculators and assemble a FeatureSet."""
        velocity_result, geo_result, graph_result = await asyncio.gather(
            self._velocity.compute(
                user_id=user_id,
                txn_id=txn_id,
                amount=amount,
                merchant_id=merchant_id,
            ),
            self._geo.compute(
                user_id=user_id,
                latitude=latitude,
                longitude=longitude,
                timestamp_iso=timestamp,
            ),
            self._graph.compute(
                user_id=user_id,
                device_fingerprint=device_fingerprint,
                ip_address=ip_address,
                merchant_id=merchant_id,
            ),
        )

        # Transaction-level features (synchronous)
        amount_zscore = compute_amount_zscore(amount, AMOUNT_MEAN, AMOUNT_STDDEV)

        try:
            dt = datetime.fromisoformat(timestamp)
            hour = dt.hour
        except (ValueError, TypeError):
            hour = 12  # default to low-risk hour

        time_risk = compute_time_of_day_risk(hour)
        high_risk_mcc = is_high_risk_mcc(mcc)
        is_first_transaction = velocity_result["txn_count_1hr"] <= 1

        return FeatureSet(
            txn_id=UUID(txn_id) if isinstance(txn_id, str) else txn_id,
            txn_count_5min=velocity_result["txn_count_5min"],
            txn_count_1hr=velocity_result["txn_count_1hr"],
            txn_amount_sum_1hr=velocity_result["txn_amount_sum_1hr"],
            unique_merchants_1hr=velocity_result["unique_merchants_1hr"],
            geo_distance_km=geo_result["geo_distance_km"],
            geo_velocity_kmh=geo_result["geo_velocity_kmh"],
            country_mismatch=geo_result["country_mismatch"],
            shared_device_count=graph_result["shared_device_count"],
            shared_ip_count=graph_result["shared_ip_count"],
            card_device_ratio=graph_result["card_device_ratio"],
            graph_risk_cluster=graph_result["graph_risk_cluster"],
            amount_zscore=amount_zscore,
            is_high_risk_mcc=high_risk_mcc,
            is_first_transaction=is_first_transaction,
            time_of_day_risk=time_risk,
        )
