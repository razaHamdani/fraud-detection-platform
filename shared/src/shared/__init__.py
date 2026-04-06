"""Shared library for fraud-detection-platform."""

__version__ = "0.1.0"

from shared.config import Settings, get_settings
from shared.feature_store import RedisFeatureStore
from shared.logging import get_logger, setup_logging
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
from shared.streams import (
    RedisStreamConsumer,
    RedisStreamPublisher,
    StreamConsumer,
    StreamPublisher,
)

__all__ = [
    # Models
    "Transaction",
    "ScoreBreakdown",
    "Decision",
    "DecisionEnum",
    "Chargeback",
    "FeatureSet",
    "Rule",
    "ScoringWeights",
    # Config
    "Settings",
    "get_settings",
    # Streams
    "RedisStreamConsumer",
    "RedisStreamPublisher",
    "StreamConsumer",
    "StreamPublisher",
    # Feature store
    "RedisFeatureStore",
    # Logging
    "setup_logging",
    "get_logger",
]
