"""
Tests for LIAMeasurementSetup's closed-loop bias auto-calibration hill-climb,
using stub set/get/measure callables instead of real GPIB hardware.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sources'))

from setups.lia_setup import LIAMeasurementSetup  # noqa: E402


def _make_setup() -> LIAMeasurementSetup:
    # Bypass __init__ (which opens a pyvisa ResourceManager) since
    # _hill_climb_to_target only needs the callables it's given.
    return object.__new__(LIAMeasurementSetup)


def _linear_probe(start: float, slope: float, offset: float):
    """A simulated instrument: measured = slope * (value - start) + offset."""
    state = {"value": start}
    return (
        lambda: state["value"],
        lambda v: state.__setitem__("value", v),
        lambda: slope * (state["value"] - start) + offset,
    )


def test_converges_increasing_direction():
    setup = _make_setup()
    get_value, set_value, measure = _linear_probe(start=1.0, slope=2e-6, offset=1e-6)
    target = 4.5e-6
    tolerance = 1e-7

    final_value = setup._hill_climb_to_target(
        get_value=get_value, set_value=set_value, measure=measure,
        target=target, tolerance=tolerance, step=0.1, min_step=0.001,
        max_steps=200, settle=0.0, label="test-increasing",
    )

    assert abs(measure() - target) <= tolerance
    assert final_value > 1.0


def test_converges_decreasing_direction():
    setup = _make_setup()
    # Negative slope: measured falls as value rises, target is below start.
    get_value, set_value, measure = _linear_probe(start=3.0, slope=-1.5e-6, offset=8e-6)
    target = 5e-6
    tolerance = 1e-7

    final_value = setup._hill_climb_to_target(
        get_value=get_value, set_value=set_value, measure=measure,
        target=target, tolerance=tolerance, step=0.1, min_step=0.001,
        max_steps=200, settle=0.0, label="test-decreasing",
    )

    assert abs(measure() - target) <= tolerance
    assert final_value != 3.0


def test_already_at_target_returns_immediately():
    setup = _make_setup()
    get_value, set_value, measure = _linear_probe(start=2.0, slope=1e-6, offset=4.5e-6)

    final_value = setup._hill_climb_to_target(
        get_value=get_value, set_value=set_value, measure=measure,
        target=4.5e-6, tolerance=1e-7, step=0.1, min_step=0.001,
        max_steps=200, settle=0.0, label="test-no-op",
    )

    assert final_value == 2.0


def test_respects_bounds_and_stops():
    setup = _make_setup()
    # Target is unreachable within [min_bound, max_bound]; search should stop
    # rather than loop forever or exceed the bound.
    get_value, set_value, measure = _linear_probe(start=2.5, slope=1e-6, offset=1e-6)
    target = 100e-6  # unreachable within bounds

    final_value = setup._hill_climb_to_target(
        get_value=get_value, set_value=set_value, measure=measure,
        target=target, tolerance=1e-9, step=0.1, min_step=0.001,
        max_steps=50, settle=0.0, label="test-bounded",
        min_bound=2.5, max_bound=3.0,
    )

    assert 2.5 <= final_value <= 3.0


def test_safety_check_aborts():
    setup = _make_setup()
    get_value, set_value, measure = _linear_probe(start=2.5, slope=1e-6, offset=1e-6)

    def trip_after_one_step():
        if get_value() > 2.5:
            raise RuntimeError("safety tripped")

    try:
        setup._hill_climb_to_target(
            get_value=get_value, set_value=set_value, measure=measure,
            target=100e-6, tolerance=1e-9, step=0.1, min_step=0.001,
            max_steps=50, settle=0.0, label="test-safety",
            safety_check=trip_after_one_step,
        )
        assert False, "expected RuntimeError from safety_check"
    except RuntimeError:
        pass
