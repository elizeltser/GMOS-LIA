"""
Parametrized tests for OperatingPointSweep.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python', 'sources'))

from config import OperatingPointSweepConfig
from setups.operating_point_sweep import OperatingPointSweep


def test_operating_point_sweep_config_defaults():
    sweep = OperatingPointSweep()
    assert sweep.config.heater_voltages == [2.5, 2.7, 3.0]
    assert sweep.config.lia_offsets == [0.8, 0.9, 1.0]
    assert len(sweep.config.scu_voltages) == 20


def test_operating_point_sweep_custom_config():
    cfg = OperatingPointSweepConfig(
        heater_voltages=[2.5],
        lia_offsets=[0.9],
        scu_voltages=[0.1, 0.2, 0.3],
        plot_offset_value=0.9,
    )
    sweep = OperatingPointSweep(config=cfg)
    assert sweep.config.heater_voltages == [2.5]
    assert sweep.config.scu_voltages == [0.1, 0.2, 0.3]
    assert sweep.config.plot_offset_value == 0.9
