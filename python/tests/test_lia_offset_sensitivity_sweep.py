"""
Parametrized tests for LIAOffsetSensitivitySweep.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python', 'sources'))

from config import LIAOffsetSensitivitySweepConfig
from setups.lia_offset_sensitivity_sweep import (
    LIAOffsetSensitivitySweep,
    _measure_current_avg,
)


def test_lia_offset_sensitivity_sweep_config_defaults():
    sweep = LIAOffsetSensitivitySweep()
    assert len(sweep.config.psu_voltages) == 6
    assert len(sweep.config.scu_bias_voltages) == 5
    assert len(sweep.config.lia_offsets) == 11
    assert sweep.config.lia_frequency == 517.0
    assert sweep.config.amplitude == 5e-3
    assert sweep.config.psu_step == 1e-3
    assert sweep.config.n_measurements == 10
    assert sweep.config.initial_settle == 60.0
    assert sweep.config.step_settle == 1.0


def test_lia_offset_sensitivity_sweep_custom_config():
    cfg = LIAOffsetSensitivitySweepConfig(
        psu_voltages=[2.5, 2.7],
        scu_bias_voltages=[1.9, 2.1],
        lia_offsets=[0.975, 0.9875, 1.0],
        psu_step=2e-3,
        n_measurements=5,
    )
    sweep = LIAOffsetSensitivitySweep(config=cfg)
    assert sweep.config.psu_voltages == [2.5, 2.7]
    assert sweep.config.scu_bias_voltages == [1.9, 2.1]
    assert sweep.config.lia_offsets == [0.975, 0.9875, 1.0]
    assert sweep.config.psu_step == 2e-3
    assert sweep.config.n_measurements == 5


class _FakeSCU:
    def __init__(self, values):
        self._values = iter(values)

    def measure_current(self, channel=1):
        return next(self._values)


def test_measure_current_avg():
    scu = _FakeSCU([1.0, 2.0, 3.0])
    mean, mse = _measure_current_avg(scu, channel=1, n=3)
    assert mean == 2.0
    assert abs(mse - (2.0 / 3.0)) < 1e-9
