"""
Tests for setups.dwell_analysis: drift fit over an ISOLATED START/END window
and the markdown report's cold-start-shift conversion.
"""

import csv
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python', 'sources'))

from config import DwellAnalysisConfig
from setups.dwell_analysis import analyze_dwell, markdown_report


def _write_dwell(path, x0, drift_v_per_s, n=3600, seed=0):
    """Constant-rate drift plus small noise, bracketed by isolation markers."""
    rng = np.random.default_rng(seed)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["LIA"])
        w.writerow(["reference_dc_V", 0.87])
        w.writerow(["index", "time_s", "R_v", "theta_deg", "event"])
        w.writerow([0, 0.0, x0, 0.0, "cold start"])
        for k in range(1, n):
            x = x0 + drift_v_per_s * k + rng.normal(0, 2e-4)
            event = "ISOLATED START" if k == 1 else (
                "ISOLATED END" if k == n - 1 else "")
            w.writerow([k, float(k), abs(x), 0.0 if x >= 0 else 180.0, event])


def test_drift_slope_recovered(tmp_path):
    p = tmp_path / "dwell.csv"
    _write_dwell(p, x0=0.5, drift_v_per_s=2e-6, n=3600)
    r = analyze_dwell(str(p))
    assert r.drift_v_per_s == pytest.approx(2e-6, rel=0.1)
    assert r.duration_h == pytest.approx(1.0, rel=0.01)
    assert r.x_start_v == pytest.approx(0.5, abs=2e-3)


def test_missing_markers_raise(tmp_path):
    p = tmp_path / "bad.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["LIA"])
        w.writerow(["reference_dc_V", 0.87])
        w.writerow(["index", "time_s", "R_v", "theta_deg", "event"])
        w.writerow([0, 0.0, 0.5, 0.0, ""])
    with pytest.raises(ValueError, match="ISOLATED"):
        analyze_dwell(str(p))


def test_report_converts_cold_start_shift_to_heater_mv(tmp_path):
    p1, p2 = tmp_path / "d1.csv", tmp_path / "d2.csv"
    _write_dwell(p1, x0=0.500, drift_v_per_s=0.0, n=600, seed=1)
    _write_dwell(p2, x0=0.510, drift_v_per_s=0.0, n=600, seed=2)  # +10 mV shift
    results = [analyze_dwell(str(p1)), analyze_dwell(str(p2))]
    report = markdown_report(results, DwellAnalysisConfig(local_slope_v_per_v=100.0))
    # 10 mV shift / 100 V/V = 0.1 mV equivalent heater voltage.
    assert "0.1" in report and "heater voltage" in report


def test_report_without_slope_omits_conversion(tmp_path):
    p1, p2 = tmp_path / "d1.csv", tmp_path / "d2.csv"
    _write_dwell(p1, x0=0.5, drift_v_per_s=0.0, n=600, seed=1)
    _write_dwell(p2, x0=0.51, drift_v_per_s=0.0, n=600, seed=2)
    results = [analyze_dwell(str(p1)), analyze_dwell(str(p2))]
    report = markdown_report(results, DwellAnalysisConfig())
    assert "heater voltage" not in report
