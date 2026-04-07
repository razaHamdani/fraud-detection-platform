"""Tests for transaction feature calculations."""

from feature_engine.transaction import (
    compute_amount_zscore,
    compute_time_of_day_risk,
    is_high_risk_mcc,
)


class TestAmountZscore:
    def test_normal_zscore(self):
        assert compute_amount_zscore(180, 100, 80) == 1.0

    def test_negative_zscore(self):
        assert compute_amount_zscore(20, 100, 80) == -1.0

    def test_zero_stddev_returns_zero(self):
        assert compute_amount_zscore(100, 100, 0) == 0.0

    def test_exact_mean_returns_zero(self):
        assert compute_amount_zscore(100, 100, 80) == 0.0


class TestTimeOfDayRisk:
    def test_midnight(self):
        assert compute_time_of_day_risk(0) == 0.8

    def test_3am(self):
        assert compute_time_of_day_risk(3) == 0.8

    def test_5am(self):
        assert compute_time_of_day_risk(5) == 0.8

    def test_6am(self):
        assert compute_time_of_day_risk(6) == 0.4

    def test_8am(self):
        assert compute_time_of_day_risk(8) == 0.4

    def test_10am(self):
        assert compute_time_of_day_risk(10) == 0.1

    def test_noon(self):
        assert compute_time_of_day_risk(12) == 0.1

    def test_10pm(self):
        assert compute_time_of_day_risk(22) == 0.6

    def test_11pm(self):
        assert compute_time_of_day_risk(23) == 0.6


class TestIsHighRiskMcc:
    def test_gambling(self):
        assert is_high_risk_mcc("7995") is True

    def test_crypto(self):
        assert is_high_risk_mcc("6051") is True

    def test_all_high_risk(self):
        for mcc in ("7995", "6051", "5967", "5816", "5960"):
            assert is_high_risk_mcc(mcc) is True

    def test_normal_mcc(self):
        assert is_high_risk_mcc("5411") is False

    def test_empty_string(self):
        assert is_high_risk_mcc("") is False
