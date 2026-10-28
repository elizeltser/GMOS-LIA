"""
Tests for setups.heater_slope_table: parsing monitor CSVs, windowed point
statistics, flags and slope uncertainty.

Synthetic monitor CSVs are built in memory, so no instruments or stored
results are needed.
"""

import csv
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python', 'sources'))

from config import HeaterSlopeTableConfig
from setups.heater_slope_table import (
    build_slopes,
    extract_points,
    parse_monitor_csv,
)


def _write_monitor(path, segments, vgs0=0.87, seed=0):
    """``segments``: list of (duration_s, x_v, event_at_start, end_note).

    X is constant per segment plus 100 uV white noise; theta is 0 (x>0) or
    180 (x<0) and R=|x|, as after a good phase zero.
    """
    rng = np.random.default_rng(seed)
    rows, t, idx = [], 0.0, 0
    for duration, x, start_event, end_note in segments:
        n = int(duration)
        for k in range(n):
            xv = x + rng.normal(0, 1e-4)
            event = ""
            if k == 0 and start_event:
                event = start_event
            if k == n - 1 and end_note:
                event = f"{event} | {end_note}" if event else end_note
            rows.append([idx, t, abs(xv), 0.0 if xv >= 0 else 180.0, event])
            idx += 1
            t += 1.0
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["LIA"])
        w.writerow(["reference_dc_V", vgs0])
        w.writerow(["index", "time_s", "R_v", "theta_deg", "event"])
        w.writerows(rows)


def _cfg(**kw):
    return HeaterSlopeTableConfig(window_s=200.0, min_settle_s=150.0, **kw)


def test_two_point_slope_matches_construction(tmp_path):
    p = tmp_path / "mon.csv"
    _write_monitor(p, [
        (400, 0.500, None, "pt(2.879): signed R=+0.5000 Vd .164/.131"),
        (400, -0.200, "heater ch1 -> 2.89V", "pt(2.890): signed R=-0.2000"),
    ])
    pts = extract_points(parse_monitor_csv(str(p)), "mon", _cfg())
    assert len(pts) == 2
    assert pts[0].ch1_v == 2.879 and pts[1].ch1_v == 2.890
    assert pts[0].x_end_v == pytest.approx(0.5, abs=5e-4)
    assert pts[1].x_end_v == pytest.approx(-0.2, abs=5e-4)
    assert pts[0].vd == (0.164, 0.131) and "vd_low" in pts[0].flags
    (slope,) = build_slopes(pts, _cfg())
    assert slope.slope_v_per_v == pytest.approx(-0.7 / 0.011, rel=1e-2)
    # Readback quantization (1 mV res, 11 mV step) dominates the noise term.
    assert slope.sigma_ch1_v_per_v > 10 * slope.sigma_stat_v_per_v
    assert slope.sigma_ch1_v_per_v / abs(slope.slope_v_per_v) == pytest.approx(
        np.sqrt(2) * 1e-3 / np.sqrt(12) / 0.011, rel=1e-6)


def test_settle_time_and_sample_count_use_last_change(tmp_path):
    p = tmp_path / "mon.csv"
    _write_monitor(p, [
        (300, 0.1, None, "pt(2.879): signed R=+0.1000"),
        (500, 0.3, "heater ch1 -> 2.89V", "pt(2.890): signed R=+0.3000"),
    ])
    a, b = extract_points(parse_monitor_csv(str(p)), "mon", _cfg())
    assert b.settle_s == pytest.approx(499, abs=1.5)  # dwell length
    assert b.n == pytest.approx(200, abs=2)  # window_s, not the whole dwell


def test_short_settle_and_over_range_points_are_flagged_and_excluded(tmp_path):
    p = tmp_path / "mon.csv"
    _write_monitor(p, [
        (300, 0.5, None, "pt(2.879): signed R=+0.5000"),
        (100, 0.6, "heater ch1 -> 2.89V", "pt(2.890): R=0.6000"),
        (300, 1.1, "heater ch1 -> 2.9V", "pt(2.900): R=1.1000"),
    ])
    pts = extract_points(parse_monitor_csv(str(p)), "mon", _cfg())
    assert "short_settle" in pts[1].flags
    assert "over_range" in pts[2].flags
    assert build_slopes(pts, _cfg()) == []


def test_visits_split_at_offset_changes(tmp_path):
    p = tmp_path / "mon.csv"
    _write_monitor(p, [
        (300, 0.5, None, "pt(2.879): signed R=+0.5000"),
        (300, 0.1, "offset -> 0.88V", "pt(2.879): signed R=+0.1000"),
    ])
    a, b = extract_points(parse_monitor_csv(str(p)), "mon", _cfg())
    assert (a.visit, b.visit) == (0, 1)
    assert (a.vgs_v, b.vgs_v) == (0.87, 0.88)
    # Same ch1 in different visits never forms a slope pair.
    assert build_slopes([a, b], _cfg()) == []


def test_phase_zero_near_null_flags_points_until_rezeroed(tmp_path):
    p = tmp_path / "mon.csv"
    _write_monitor(p, [
        (300, 0.05, None, None),
        (300, 0.05, "auto-phase converged (sigma=0.1deg)",
         "pt(2.874): signed R=+0.0500"),
        (300, 0.50, "heater ch1 -> 2.88V", None),
        (300, 0.50, "auto-phase converged (sigma=0.01deg)",
         "pt(2.879): signed R=+0.5000"),
    ])
    a, b = extract_points(parse_monitor_csv(str(p)), "mon", _cfg())
    assert "phase_suspect" in a.flags
    assert "phase_suspect" not in b.flags


def test_logged_ch1_readback_is_cross_checked(tmp_path):
    p = tmp_path / "mon.csv"
    _write_monitor(p, [
        (300, 0.5, "heater ch1 -> 2.879V (readback 2.879V)",
         "pt(2.879): signed R=+0.5000"),
        (300, 0.4, "heater ch1 -> 2.875V (readback 2.874V)",
         "pt(2.879): signed R=+0.4000"),
    ])
    a, b = extract_points(parse_monitor_csv(str(p)), "mon", _cfg())
    assert "ch1_mismatch" not in a.flags
    assert "ch1_mismatch" in b.flags  # note claims 2.879, PSU read back 2.874


def test_note_value_is_cross_checked(tmp_path):
    p = tmp_path / "mon.csv"
    _write_monitor(p, [(300, 0.5, None, "pt(2.879): signed R=+0.4000")])
    (pt,) = extract_points(parse_monitor_csv(str(p)), "mon", _cfg())
    assert pt.note_signed_r_v == 0.4
    assert pt.mean_x_v - pt.note_signed_r_v == pytest.approx(0.1, abs=1e-3)
