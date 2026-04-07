"""Velocity-based feature calculator using Redis sliding windows."""

from shared.feature_store import RedisFeatureStore


class VelocityCalculator:
    """Compute transaction velocity features from Redis sliding windows."""

    def __init__(self, feature_store: RedisFeatureStore) -> None:
        self._store = feature_store

    async def compute(
        self,
        user_id: str,
        txn_id: str,
        amount: float,
        merchant_id: str,
    ) -> dict:
        """Compute velocity features for a transaction.

        Returns dict with:
            txn_count_5min, txn_count_1hr, unique_merchants_1hr, txn_amount_sum_1hr
        """
        txn_count_5min = await self._store.record_and_count(
            key=f"velocity:txn_count_5min:{user_id}",
            window_seconds=300,
            member=txn_id,
        )

        txn_count_1hr = await self._store.record_and_count(
            key=f"velocity:txn_count_1hr:{user_id}",
            window_seconds=3600,
            member=txn_id,
        )

        unique_merchants_1hr = await self._store.record_and_count(
            key=f"velocity:unique_merchants_1hr:{user_id}",
            window_seconds=3600,
            member=merchant_id,
        )

        txn_amount_sum_1hr = await self._store.record_sum(
            key=f"velocity:txn_amount_sum_1hr:{user_id}",
            window_seconds=3600,
            member=txn_id,
            amount=amount,
        )

        return {
            "txn_count_5min": txn_count_5min,
            "txn_count_1hr": txn_count_1hr,
            "unique_merchants_1hr": unique_merchants_1hr,
            "txn_amount_sum_1hr": txn_amount_sum_1hr,
        }
