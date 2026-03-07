"""
Parametrized tests for GMOS experiments.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python', 'sources'))

from setups.iv_sweep import IVSweep


@pytest.mark.parametrize("start,stop,step", [
    (0, 1, 0.1),
    (0, 5, 0.5),
])
def test_linear_iv_sweep(start, stop, step):
    sweep = IVSweep(start=start, stop=stop, step=step, scale='linear')
    # Mock or actual run, but for now just instantiate
    assert sweep.start == start