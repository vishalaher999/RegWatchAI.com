"""
Tests for F1 anomaly detection.

Uses in-memory SQLite and monkeypatching to test statistical logic
without needing real historical data.
"""

import pytest
from src.f1_ingest.anomaly import _mean, _std, _zscore, VOLUME_Z_THRESHOLD


# ── Unit tests for statistical helpers ────────────────────────────────────────

def test_mean_typical():
    assert _mean([1, 2, 3, 4, 5]) == pytest.approx(3.0)


def test_mean_empty():
    assert _mean([]) == 0.0


def test_std_typical():
    # Sample std (divides by n-1) for [2,4,4,4,5,5,7,9] is ~2.138
    values = [2, 4, 4, 4, 5, 5, 7, 9]
    mean = _mean(values)
    result = _std(values, mean)
    assert result == pytest.approx(2.138, rel=0.01)


def test_std_zero_variance():
    values = [5, 5, 5, 5]
    assert _std(values, 5.0) == 0.0


def test_std_single_value():
    assert _std([10], 10.0) == 0.0


def test_zscore_above_threshold():
    # Mean=2, std=1 → today=5 → z=3.0 → anomaly
    z = _zscore(5.0, mean=2.0, std=1.0)
    assert z > VOLUME_Z_THRESHOLD


def test_zscore_normal():
    # Mean=10, std=2 → today=11 → z=0.5 → not anomaly
    z = _zscore(11.0, mean=10.0, std=2.0)
    assert z < VOLUME_Z_THRESHOLD


def test_zscore_zero_std():
    # If std is 0 (perfectly stable history), never flag as anomaly
    z = _zscore(100.0, mean=2.0, std=0.0)
    assert z == 0.0


def test_zscore_negative_not_anomaly():
    # Below-average days should never be anomalies (we only care about spikes)
    z = _zscore(0.0, mean=5.0, std=1.0)
    assert z < VOLUME_Z_THRESHOLD


# ── Threshold sanity check ─────────────────────────────────────────────────────

def test_threshold_is_two():
    """The Z-score threshold must be 2.0 — a documented product decision."""
    assert VOLUME_Z_THRESHOLD == 2.0
