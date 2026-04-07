"""Geographic feature calculator with haversine distance and velocity."""

import math
from typing import Any, Optional


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    R = 6371.0  # Earth radius in km

    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def compute_geo_velocity(distance_km: float, time_delta_seconds: float) -> float:
    """Compute travel velocity in km/h. Returns inf if time_delta is zero."""
    if time_delta_seconds == 0:
        return float("inf")
    return distance_km / (time_delta_seconds / 3600)


class GeoCalculator:
    """Compute geographic features using Redis for last-known location."""

    LOCATION_TTL = 86400  # 24 hours

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    async def compute(
        self,
        user_id: str,
        latitude: float,
        longitude: float,
        timestamp_iso: str,
    ) -> dict:
        """Compute geo features for a transaction.

        Returns dict with:
            geo_distance_km, geo_velocity_kmh, country_mismatch
        """
        key = f"geo:last_location:{user_id}"
        last = await self._redis.hgetall(key)

        distance_km = 0.0
        velocity_kmh = 0.0

        if last:
            last_lat = float(last.get("latitude", last.get(b"latitude", 0)))
            last_lon = float(last.get("longitude", last.get(b"longitude", 0)))
            last_ts = last.get("timestamp", last.get(b"timestamp", ""))
            if isinstance(last_ts, bytes):
                last_ts = last_ts.decode()

            distance_km = haversine_km(last_lat, last_lon, latitude, longitude)

            from datetime import datetime, timezone

            try:
                current_dt = datetime.fromisoformat(timestamp_iso)
                last_dt = datetime.fromisoformat(last_ts)
                delta_seconds = abs((current_dt - last_dt).total_seconds())
                velocity_kmh = compute_geo_velocity(distance_km, delta_seconds)
            except (ValueError, TypeError):
                velocity_kmh = 0.0

        # Update last known location
        await self._redis.hset(
            key,
            mapping={
                "latitude": str(latitude),
                "longitude": str(longitude),
                "timestamp": timestamp_iso,
            },
        )
        await self._redis.expire(key, self.LOCATION_TTL)

        return {
            "geo_distance_km": distance_km,
            "geo_velocity_kmh": velocity_kmh,
            "country_mismatch": False,
        }
