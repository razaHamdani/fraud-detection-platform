"""Tests for geographic feature calculator."""

import math
from unittest.mock import AsyncMock

import pytest

from feature_engine.geo import GeoCalculator, compute_geo_velocity, haversine_km


class TestHaversine:
    def test_nyc_to_la(self):
        # NYC: 40.7128, -74.0060 | LA: 34.0522, -118.2437
        distance = haversine_km(40.7128, -74.0060, 34.0522, -118.2437)
        assert abs(distance - 3944) < 10  # ~3944 km

    def test_same_point(self):
        distance = haversine_km(51.5074, -0.1278, 51.5074, -0.1278)
        assert distance == 0.0

    def test_antipodal_points(self):
        # North pole to south pole
        distance = haversine_km(90, 0, -90, 0)
        assert abs(distance - math.pi * 6371) < 1


class TestGeoVelocity:
    def test_normal_velocity(self):
        # 100 km in 3600 seconds = 100 km/h
        velocity = compute_geo_velocity(100.0, 3600.0)
        assert velocity == 100.0

    def test_zero_time_returns_inf(self):
        velocity = compute_geo_velocity(100.0, 0)
        assert velocity == float("inf")

    def test_zero_distance(self):
        velocity = compute_geo_velocity(0.0, 3600.0)
        assert velocity == 0.0


class TestGeoCalculator:
    @pytest.fixture
    def redis_client(self):
        client = AsyncMock()
        client.hgetall = AsyncMock(return_value={})
        client.hset = AsyncMock()
        client.expire = AsyncMock()
        return client

    @pytest.fixture
    def calculator(self, redis_client):
        return GeoCalculator(redis_client)

    @pytest.mark.asyncio
    async def test_first_transaction_no_previous_location(self, calculator):
        result = await calculator.compute(
            user_id="user-1",
            latitude=40.7128,
            longitude=-74.0060,
            timestamp_iso="2024-01-01T12:00:00+00:00",
        )

        assert result["geo_distance_km"] == 0.0
        assert result["geo_velocity_kmh"] == 0.0
        assert result["country_mismatch"] is False

    @pytest.mark.asyncio
    async def test_with_previous_location(self, redis_client):
        redis_client.hgetall = AsyncMock(
            return_value={
                "latitude": "40.7128",
                "longitude": "-74.0060",
                "timestamp": "2024-01-01T12:00:00+00:00",
            }
        )
        calculator = GeoCalculator(redis_client)

        result = await calculator.compute(
            user_id="user-1",
            latitude=34.0522,
            longitude=-118.2437,
            timestamp_iso="2024-01-01T13:00:00+00:00",
        )

        assert abs(result["geo_distance_km"] - 3944) < 10
        # ~3944 km in 1 hour = ~3944 km/h
        assert abs(result["geo_velocity_kmh"] - 3944) < 10

    @pytest.mark.asyncio
    async def test_updates_last_location(self, calculator, redis_client):
        await calculator.compute(
            user_id="user-1",
            latitude=51.5074,
            longitude=-0.1278,
            timestamp_iso="2024-01-01T12:00:00+00:00",
        )

        redis_client.hset.assert_called_once_with(
            "geo:last_location:user-1",
            mapping={
                "latitude": "51.5074",
                "longitude": "-0.1278",
                "timestamp": "2024-01-01T12:00:00+00:00",
            },
        )
        redis_client.expire.assert_called_once_with(
            "geo:last_location:user-1", 86400
        )

    @pytest.mark.asyncio
    async def test_zero_time_delta_returns_inf(self, redis_client):
        redis_client.hgetall = AsyncMock(
            return_value={
                "latitude": "40.7128",
                "longitude": "-74.0060",
                "timestamp": "2024-01-01T12:00:00+00:00",
            }
        )
        calculator = GeoCalculator(redis_client)

        result = await calculator.compute(
            user_id="user-1",
            latitude=34.0522,
            longitude=-118.2437,
            timestamp_iso="2024-01-01T12:00:00+00:00",
        )

        assert result["geo_velocity_kmh"] == float("inf")
