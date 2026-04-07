"""Tests for TransactionSimulator."""
import pytest

from shared.models import Transaction
from stream_ingester.simulator import TransactionSimulator


@pytest.fixture
def simulator():
    return TransactionSimulator(seed=42)


def test_generate_normal_returns_valid_transaction(simulator):
    txn = simulator.generate(fraud_type="normal")
    assert isinstance(txn, Transaction)
    assert 5 <= txn.amount <= 200


def test_generate_suspicious_returns_valid_transaction(simulator):
    txn = simulator.generate(fraud_type="suspicious")
    assert isinstance(txn, Transaction)
    assert 200 <= txn.amount <= 2000


def test_generate_fraud_returns_valid_transaction(simulator):
    txn = simulator.generate(fraud_type="fraud")
    assert isinstance(txn, Transaction)
    assert 500 <= txn.amount <= 15000


def test_generate_random_returns_transaction_and_label(simulator):
    txn, label = simulator.generate_random()
    assert isinstance(txn, Transaction)
    assert label in ("normal", "suspicious", "fraud")


def test_generate_random_distribution_roughly_matches():
    sim = TransactionSimulator(seed=123)
    counts = {"normal": 0, "suspicious": 0, "fraud": 0}
    n = 5000
    for _ in range(n):
        _, label = sim.generate_random()
        counts[label] += 1

    # Allow generous margins: normal 80-96%, suspicious 3-15%, fraud 0.5-6%
    assert 0.80 <= counts["normal"] / n <= 0.96, f"normal ratio: {counts['normal']/n}"
    assert 0.03 <= counts["suspicious"] / n <= 0.15, f"suspicious ratio: {counts['suspicious']/n}"
    assert 0.005 <= counts["fraud"] / n <= 0.06, f"fraud ratio: {counts['fraud']/n}"


def test_seed_produces_reproducible_results():
    sim1 = TransactionSimulator(seed=99)
    sim2 = TransactionSimulator(seed=99)
    txn1 = sim1.generate(fraud_type="normal")
    txn2 = sim2.generate(fraud_type="normal")
    assert txn1.amount == txn2.amount
    assert txn1.latitude == txn2.latitude
