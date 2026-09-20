"""
Tests for mcp_server.operating_point_session.OperatingPointSession.

Fake LIA/SCU/PSU objects are injected directly into the session's private
handles, bypassing real instrument opening entirely (mirrors the fake-object
pattern used by test_lia_offset_sensitivity_sweep.py's ``_FakeSCU``).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python', 'sources'))

from mcp_server import bounds
from mcp_server.errors import DrainVoltageError, MonitorStateError, OutOfRangeError
from mcp_server.operating_point_session import OperatingPointSession


class _FakeLIA:
    def __init__(self, offset=1.0):
        self._offset = offset
        self.set_offset_calls = []

    def set_offset(self, value):
        self.set_offset_calls.append(value)
        self._offset = value

    def get_offset(self):
        return self._offset


class _FakeSCU:
    def __init__(self, currents):
        self._currents = iter(currents)
        self.voltage = 0.0
        self.set_voltage_calls = []

    def set_source_function(self, func, compliance, channel=1):
        pass

    def set_voltage(self, voltage, channel=1):
        self.voltage = voltage
        self.set_voltage_calls.append(voltage)

    def get_voltage(self, channel=1):
        return self.voltage

    def enable_output(self, channel=1):
        pass

    def measure_current(self, channel=1):
        return next(self._currents)


@pytest.fixture(autouse=True)
def _no_real_settle(monkeypatch):
    # set_drain_voltage sleeps SETTLE_AFTER_SETPOINT_S between setpoint and
    # measurement; skip the real delay in tests.
    monkeypatch.setattr(bounds, "SETTLE_AFTER_SETPOINT_S", 0.0)


def _session_with_fake_lia(offset=1.0):
    session = OperatingPointSession()
    session._lia = _FakeLIA(offset)
    return session


def test_set_offset_out_of_range_never_reaches_lia():
    session = _session_with_fake_lia()
    with pytest.raises(OutOfRangeError):
        session.set_offset(1.5)
    assert session._lia.set_offset_calls == []


def test_set_offset_in_range_applies_and_reads_back():
    session = _session_with_fake_lia()
    result = session.set_offset(0.95)
    assert result["offset_v"] == 0.95
    assert session._lia.set_offset_calls == [0.95]


def _session_with_fake_scu(currents, previous_voltage=1.0):
    session = OperatingPointSession()
    session._lia = _FakeLIA()
    scu = _FakeSCU(currents)
    session._scu1 = scu
    session._last_good_voltage["SCU1"] = previous_voltage
    return session, scu


def test_set_drain_voltage_success_within_bounds():
    # voltage_v=3.0, current=8uA -> Vd = 3.0 - 330e3*8e-6 = 0.36V, above 150mV.
    session, scu = _session_with_fake_scu([8e-6])
    result = session.set_drain_voltage("SCU1", 3.0)
    assert result["current_a"] == 8e-6
    assert result["vd_v"] == pytest.approx(3.0 - bounds.SERIES_RESISTANCE_OHM * 8e-6)
    assert session._last_good_voltage["SCU1"] == 3.0


def test_set_drain_voltage_rolls_back_on_low_vd():
    # Vd = 3.0 - 330e3*9e-6 = 3.0 - 2.97 = 0.03V <= 150mV -> rejected
    session, scu = _session_with_fake_scu([9e-6], previous_voltage=1.23)
    with pytest.raises(DrainVoltageError):
        session.set_drain_voltage("SCU1", 3.0)
    # Rolled back to the previous known-good voltage.
    assert scu.set_voltage_calls[-1] == 1.23
    assert session._last_good_voltage["SCU1"] == 1.23


def test_set_drain_voltage_rolls_back_on_current_out_of_range():
    # voltage_v=6.0, current=15uA -> Vd = 6.0 - 330e3*15e-6 = 6.0 - 4.95 = 1.05V,
    # comfortably above 150mV, but 15uA is outside the 7-10uA target range.
    session, scu = _session_with_fake_scu([15e-6], previous_voltage=0.5)
    with pytest.raises(OutOfRangeError):
        session.set_drain_voltage("SCU1", 6.0)
    assert scu.set_voltage_calls[-1] == 0.5
    assert session._last_good_voltage["SCU1"] == 0.5


def test_close_is_idempotent_when_nothing_was_opened():
    session = OperatingPointSession()
    result1 = session.close()
    result2 = session.close()
    assert result1["status"] == "closed"
    assert result2["status"] == "already_closed"


def test_monitor_status_without_a_started_monitor_raises():
    session = OperatingPointSession()
    with pytest.raises(MonitorStateError):
        session.monitor_status()
