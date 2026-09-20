"""
Tests for mcp_server.continuous_monitor.ContinuousMonitor.
"""

import csv
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python', 'sources'))

from mcp_server.continuous_monitor import ContinuousMonitor
from setups.setup_base import SetupSnapshot


def _wait_until(predicate, timeout=5.0, interval=0.01):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def test_continuous_monitor_logs_samples_and_computes_drift(tmp_path):
    # Deterministic increasing R: R = 1.0 + 0.01 * sample_index.
    samples = iter((1.0 + 0.01 * i, 0.0) for i in range(20))

    def read_sample():
        return next(samples)

    csv_path = str(tmp_path / "monitor.csv")
    monitor = ContinuousMonitor(
        read_sample,
        csv_path,
        SetupSnapshot(),
        sample_interval=0.01,
        drift_window_s=60.0,
    )
    monitor.start()
    try:
        assert _wait_until(lambda: monitor.status()["n_samples"] >= 15)
    finally:
        result = monitor.stop()

    assert result["n_samples"] >= 15
    # Slope should be ~1 V/s (0.01V per 0.01s sample_interval).
    assert result["drift_slope_v_per_s"] == pytest.approx(1.0, rel=0.5)

    with open(csv_path, newline="") as f:
        rows = list(csv.reader(f))
    header_row = next(r for r in rows if r and r[0] == "index")
    assert header_row == ["index", "time_s", "R_v", "theta_deg", "event"]
    data_rows = rows[rows.index(header_row) + 1:]
    assert len(data_rows) == result["n_samples"]


def test_add_event_attaches_note_to_next_row(tmp_path):
    samples = iter((float(i), 0.0) for i in range(10))

    def read_sample():
        return next(samples)

    csv_path = str(tmp_path / "monitor.csv")
    monitor = ContinuousMonitor(
        read_sample, csv_path, SetupSnapshot(), sample_interval=0.01
    )
    monitor.start()
    try:
        assert _wait_until(lambda: monitor.status()["n_samples"] >= 1)
        row_index = monitor.add_event("trying offset=0.97V")
        assert _wait_until(lambda: monitor.status()["n_samples"] > row_index)
    finally:
        monitor.stop()

    _, _, _, events = monitor.buffer()
    assert (row_index, "trying offset=0.97V") in events
