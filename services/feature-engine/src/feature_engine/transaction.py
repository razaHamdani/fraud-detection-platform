"""Transaction-level feature calculations."""

HIGH_RISK_MCCS = {"7995", "6051", "5967", "5816", "5960"}


def compute_amount_zscore(amount: float, mean: float, stddev: float) -> float:
    """Compute z-score for transaction amount. Returns 0 if stddev is 0."""
    if stddev == 0:
        return 0.0
    return (amount - mean) / stddev


def compute_time_of_day_risk(hour: int) -> float:
    """Return risk score based on hour of day (0-23)."""
    if 0 <= hour < 6:
        return 0.8
    elif 6 <= hour < 9:
        return 0.4
    elif 22 <= hour <= 23:
        return 0.6
    else:
        return 0.1


def is_high_risk_mcc(mcc: str) -> bool:
    """Check if merchant category code is in the high-risk set."""
    return mcc in HIGH_RISK_MCCS
