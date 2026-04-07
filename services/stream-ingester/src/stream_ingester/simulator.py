"""Transaction simulator for testing and development."""
import random
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from shared.models import Transaction

COMMON_MCCS = ["5411", "5541", "5812", "5912", "5999"]
HIGH_RISK_MCCS = ["7995", "6051", "5944", "4829", "5122"]

NORMAL_MERCHANTS = ["merchant-grocery", "merchant-gas", "merchant-restaurant"]
SUSPICIOUS_MERCHANTS = ["merchant-electronics", "merchant-jewelry", "merchant-crypto"]
FRAUD_MERCHANTS = ["merchant-offshore", "merchant-shell-corp", "merchant-dark"]

DEVICES = [f"device-{i:03d}" for i in range(50)]
SINGLE_FRAUD_DEVICE = "device-fraud-001"


class TransactionSimulator:
    """Generates synthetic transactions for testing."""

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    def generate(self, fraud_type: str = "normal") -> Transaction:
        """Generate a transaction of the given type."""
        if fraud_type == "normal":
            return self._generate_normal()
        elif fraud_type == "suspicious":
            return self._generate_suspicious()
        elif fraud_type == "fraud":
            return self._generate_fraud()
        else:
            raise ValueError(f"Unknown fraud_type: {fraud_type}")

    def generate_random(self) -> tuple[Transaction, str]:
        """Generate a random transaction with distribution: 90% normal, 8% suspicious, 2% fraud."""
        roll = self._rng.random()
        if roll < 0.90:
            return self.generate("normal"), "normal"
        elif roll < 0.98:
            return self.generate("suspicious"), "suspicious"
        else:
            return self.generate("fraud"), "fraud"

    def _generate_normal(self) -> Transaction:
        return Transaction(
            txn_id=uuid4(),
            user_id=f"user-{self._rng.randint(1, 10000):05d}",
            amount=round(self._rng.uniform(5, 200), 2),
            currency="USD",
            merchant_id=self._rng.choice(NORMAL_MERCHANTS),
            mcc=self._rng.choice(COMMON_MCCS),
            timestamp=datetime.now(tz=timezone.utc),
            latitude=round(self._rng.uniform(25, 48), 6),
            longitude=round(self._rng.uniform(-122, -73), 6),
            device_fingerprint=self._rng.choice(DEVICES),
            ip_address=f"192.168.{self._rng.randint(0, 255)}.{self._rng.randint(1, 254)}",
        )

    def _generate_suspicious(self) -> Transaction:
        return Transaction(
            txn_id=uuid4(),
            user_id=f"user-{self._rng.randint(1, 10000):05d}",
            amount=round(self._rng.uniform(200, 2000), 2),
            currency=self._rng.choice(["USD", "EUR", "GBP"]),
            merchant_id=self._rng.choice(SUSPICIOUS_MERCHANTS),
            mcc=self._rng.choice(HIGH_RISK_MCCS),
            timestamp=datetime.now(tz=timezone.utc),
            latitude=round(self._rng.uniform(25, 48), 6),
            longitude=round(self._rng.uniform(-122, -73), 6),
            device_fingerprint=self._rng.choice(DEVICES[:5]),  # shared devices
            ip_address=f"10.0.{self._rng.randint(0, 255)}.{self._rng.randint(1, 254)}",
        )

    def _generate_fraud(self) -> Transaction:
        return Transaction(
            txn_id=uuid4(),
            user_id=f"user-{self._rng.randint(1, 10000):05d}",
            amount=round(self._rng.uniform(500, 15000), 2),
            currency=self._rng.choice(["USD", "EUR", "GBP", "JPY"]),
            merchant_id=self._rng.choice(FRAUD_MERCHANTS),
            mcc=self._rng.choice(HIGH_RISK_MCCS),
            timestamp=datetime.now(tz=timezone.utc),
            latitude=round(self._rng.uniform(-60, 70), 6),  # wild geo jumps
            longitude=round(self._rng.uniform(-180, 180), 6),
            device_fingerprint=SINGLE_FRAUD_DEVICE,
            ip_address=f"203.0.{self._rng.randint(0, 255)}.{self._rng.randint(1, 254)}",
        )
