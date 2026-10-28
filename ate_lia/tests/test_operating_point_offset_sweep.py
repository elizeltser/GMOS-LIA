"""
Parametrized tests for OperatingPointOffsetSweep.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python', 'sources'))

from config import OperatingPointOffsetSweepConfig
from setups.operating_point_offset_sweep import OperatingPointOffsetSweep


def test_operating_point_offset_sweep_config_defaults():
    sweep = OperatingPointOffsetSweep()
    assert len(sweep.config.heater_voltages) == 6
    assert len(sweep.config.lia_offsets) == 6
    assert sweep.config.v_scu1 == 2.01
    assert sweep.config.v_scu2 == 2.0


def test_operating_point_offset_sweep_custom_config():
    cfg = OperatingPointOffsetSweepConfig(
        heater_voltages=[2.5, 2.7],
        lia_offsets=[0.8, 0.9, 1.0],
        v_scu1=2.05,
        v_scu2=1.95,
    )
    sweep = OperatingPointOffsetSweep(config=cfg)
    assert sweep.config.heater_voltages == [2.5, 2.7]
    assert sweep.config.lia_offsets == [0.8, 0.9, 1.0]
    assert sweep.config.v_scu1 == 2.05
    assert sweep.config.v_scu2 == 1.95
