"""Tests for the heater-resistance fit, config loading and plotting (no hardware)."""

import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sources'))

from config import HeaterResistanceConfig, load_config
from plotting import HeaterResistanceCompiler
from plotting.lia_analysis import fit_iv


def test_fit_iv_recovers_resistance_and_r2():
    v = np.linspace(0.5, 5, 10)
    fit = fit_iv(v, v / 1200.0)
    assert abs(fit["resistance"] - 1200.0) < 1e-6
    assert fit["r2"] > 0.999999
    assert fit["mse"] < 1e-20


def test_fit_iv_noisy_has_lower_r2_and_positive_mse():
    v = np.linspace(0.5, 5, 10)
    i = v / 1000.0 + np.tile([1e-4, -1e-4], 5)
    fit = fit_iv(v, i)
    assert fit["r2"] < 1.0 and fit["mse"] > 0


def test_toml_loading(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('[experiment]\nn_samples = 7\n[experiment.heater_voltages]\n'
                 'start = 1.0\nstop = 3.0\nnum = 3\n')
    _, cfg = load_config(p, HeaterResistanceConfig)
    assert cfg is not None
    assert cfg.n_samples == 7 and cfg.heater_voltages == [1.0, 2.0, 3.0]
    assert cfg.sample_interval == 0.0005 and cfg.n_repeats == 3


def test_compiler_writes_plot(tmp_path):
    path = tmp_path / "heater_resistance.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["repeat", "channel", "set_voltage", "mean_voltage",
                    "mean_current", "std_current", "sem_current", "n_samples"])
        for rep in (1, 2):
            for v in (1.0, 2.0, 3.0, 4.0):
                w.writerow([rep, 1, v, v, v / 1000 + rep * 1e-5, 0, 0, 5])
    out = HeaterResistanceCompiler(str(path)).compile()
    assert len(out) == 1 and os.path.exists(out[0])
