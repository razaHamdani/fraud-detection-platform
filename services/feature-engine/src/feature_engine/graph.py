"""Neo4j graph-based feature calculator with graceful degradation."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)

_UPSERT_QUERY = """
MERGE (u:User {id: $user_id})
MERGE (d:Device {fingerprint: $device_fingerprint})
MERGE (ip:IP {address: $ip_address})
MERGE (m:Merchant {id: $merchant_id})
MERGE (u)-[:USES_DEVICE]->(d)
MERGE (u)-[:USES_IP]->(ip)
MERGE (u)-[:TRANSACTS_WITH]->(m)
"""

_FEATURE_QUERY = """
MATCH (u:User {id: $user_id})
OPTIONAL MATCH (u)-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(other:User)
WHERE other.id <> $user_id
WITH u, count(DISTINCT other) AS shared_device_count
OPTIONAL MATCH (u)-[:USES_IP]->(ip:IP)<-[:USES_IP]-(other2:User)
WHERE other2.id <> $user_id
WITH u, shared_device_count, count(DISTINCT other2) AS shared_ip_count
OPTIONAL MATCH (u)-[:USES_DEVICE]->(d2:Device)
WITH shared_device_count, shared_ip_count,
     CASE WHEN count(d2) = 0 THEN 1.0
          ELSE toFloat(1) / toFloat(count(d2))
     END AS card_device_ratio
RETURN shared_device_count, shared_ip_count, card_device_ratio
"""

SAFE_DEFAULTS = {
    "shared_device_count": 0,
    "shared_ip_count": 0,
    "card_device_ratio": 1.0,
    "graph_risk_cluster": False,
}

TIMEOUT_SECONDS = 5.0


class GraphCalculator:
    """Compute graph-based features from Neo4j with graceful degradation."""

    def __init__(self, driver: Any) -> None:
        self._driver = driver
        self._executor = ThreadPoolExecutor(max_workers=2)

    def _run_queries(
        self,
        user_id: str,
        device_fingerprint: str,
        ip_address: str,
        merchant_id: str,
    ) -> dict:
        """Execute Neo4j queries synchronously (called from thread pool)."""
        params = {
            "user_id": user_id,
            "device_fingerprint": device_fingerprint,
            "ip_address": ip_address,
            "merchant_id": merchant_id,
        }

        with self._driver.session() as session:
            session.run(_UPSERT_QUERY, params)

            result = session.run(_FEATURE_QUERY, {"user_id": user_id})
            record = result.single()

            if record is None:
                return dict(SAFE_DEFAULTS)

            return {
                "shared_device_count": record["shared_device_count"],
                "shared_ip_count": record["shared_ip_count"],
                "card_device_ratio": record["card_device_ratio"],
                "graph_risk_cluster": False,
            }

    async def compute(
        self,
        user_id: str,
        device_fingerprint: str,
        ip_address: str,
        merchant_id: str,
    ) -> dict:
        """Compute graph features with timeout and graceful degradation.

        Returns dict with:
            shared_device_count, shared_ip_count, card_device_ratio, graph_risk_cluster
        """
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    self._executor,
                    self._run_queries,
                    user_id,
                    device_fingerprint,
                    ip_address,
                    merchant_id,
                ),
                timeout=TIMEOUT_SECONDS,
            )
            return result
        except Exception:
            logger.warning(
                "Graph feature computation degraded for user %s",
                user_id,
                exc_info=True,
            )
            return dict(SAFE_DEFAULTS)
