"""
Stateful hardware session for interactive GMOS operating-point discovery.

Unlike every other module under ``setups/``, this is not a ``SetupBase.run()``
batch experiment: it holds LIA/SCU1/SCU2/PSU instrument handles open across
many separate calls (one per MCP tool invocation from a Claude co-worker),
validates every setpoint against ``bounds`` before writing to hardware, and
exposes a background continuous-R-monitoring session for drift-aware search.
"""

import logging
import os
import threading
import time
from datetime import datetime

import ATE
from config import ATEConfig, LIAInstrumentConfig

from setups.lia_setup import LIAMeasurementSetup, sigma_phase_zero
from setups.setup_base import SetupBase

from . import bounds
from .continuous_monitor import ContinuousMonitor
from .errors import (
    DrainVoltageError,
    InstrumentIOError,
    MonitorStateError,
    OutOfRangeError,
)

logger = logging.getLogger(__name__)

_CHANNEL_TO_SCU_TAG = {"SCU1": "SCU1", "SCU2": "SCU2"}


class OperatingPointSession(SetupBase):
    """Holds live SCU1/SCU2/LIA/PSU handles across many MCP tool calls."""

    def __init__(
        self,
        ate_config: ATEConfig = None,  # type: ignore
        output_name: str = None,  # type: ignore
    ) -> None:
        super().__init__(output_name=output_name, ate_config=ate_config)
        self.results_dir = os.path.join(
            "Results", "OperatingPointSession", datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        os.makedirs(self.results_dir, exist_ok=True)

        self._lia: "ATE.LIA | None" = None
        self._scu1: "ATE.SCU | None" = None
        self._scu2: "ATE.SCU | None" = None
        self._psu: "ATE.PSU | None" = None
        self._monitor: ContinuousMonitor | None = None
        self._lock = threading.RLock()
        self._closed = False
        self._last_good_voltage: dict[str, float] = {"SCU1": 0.0, "SCU2": 0.0}

    # -- lifecycle ---------------------------------------------------------

    def open_instruments(self) -> dict:
        with self._lock:
            if self._lia is not None:
                return {"status": "already_open"}
            self._closed = False
            try:
                self._lia = self.open_no_reset(ATE.LIA(rm=self.rm))
                self._scu1 = self.open_no_reset(ATE.SCU("SCU1", rm=self.rm))
                self._scu2 = self.open_no_reset(ATE.SCU("SCU2", rm=self.rm))
                self._psu = self.open_no_reset(ATE.PSU(rm=self.rm))

                lia_idn = self._lia.idn().strip()
                psu_idn = self._psu.idn().strip()

                cfg = self.ate_config
                self._psu.set_voltage(2, cfg.esd_voltage)
                self._psu.set_current(2, cfg.esd_current)
                self._psu.enable_output(2)
                self._psu.set_voltage(4, cfg.fan_voltage)
                self._psu.set_current(4, cfg.fan_current)
                self._psu.enable_output(4)
            except Exception as exc:
                raise InstrumentIOError("session", "open_instruments", exc) from exc
            return {"status": "opened", "lia_idn": lia_idn, "psu_idn": psu_idn}

    def configure_signal(
        self,
        config: LIAInstrumentConfig = None,  # type: ignore
        frequency_hz: float = 518.0,
    ) -> dict:
        """Apply LIA excitation/filter settings (amplitude, frequency,
        sensitivity, filter slope, time constant, input coupling/source/range)
        from ``config`` (defaults to ``LIAInstrumentConfig()``). Offset and
        SCU drain voltage are set separately via ``set_offset``/
        ``set_drain_voltage`` since those are the interactively-explored
        knobs."""
        cfg = config or LIAInstrumentConfig()
        bounds.check_range("amplitude", cfg.amplitude, 0.0, bounds.AMPLITUDE_MAX_V)
        self.open_instruments()
        with self._lock:
            try:
                lia = self._lia
                assert lia is not None
                lia.set_frequency(frequency_hz)
                lia.set_amplitude(cfg.amplitude)
                lia.set_sensitivity(cfg.sensitivity)
                lia.set_filter_slope(cfg.filter_slope)
                lia.set_time_constant(cfg.time_constant)
                lia.set_input_coupling(cfg.input_coupling)
                lia.set_input_source(cfg.input_source)
                lia.set_input_range(cfg.input_range)
                frequency_readback = lia.get_frequency()
            except Exception as exc:
                raise InstrumentIOError("LIA", "configure_signal", exc) from exc
        return {
            "frequency_hz": frequency_readback,
            "amplitude_v": cfg.amplitude,
            "sensitivity": cfg.sensitivity.name,
            "filter_slope": cfg.filter_slope.name,
            "time_constant": cfg.time_constant.name,
        }

    def close(self) -> dict:
        with self._lock:
            if self._closed:
                return {"status": "already_closed"}
            if self._monitor is not None and self._monitor.status()["running"]:
                try:
                    self._monitor.stop()
                except Exception:
                    logger.exception("error stopping monitor during close()")
            any_opened = any(
                h is not None for h in (self._lia, self._scu1, self._scu2, self._psu)
            )
            # Close our still-open handles first: _shutdown_all_devices opens
            # its own fresh sessions on the same GPIB addresses, which would
            # conflict with sessions we're still holding.
            for handle in (self._lia, self._scu1, self._scu2, self._psu):
                if handle is not None:
                    try:
                        handle.resource.close()
                    except Exception:
                        pass
            self._lia = self._scu1 = self._scu2 = self._psu = None
            if any_opened:
                LIAMeasurementSetup._shutdown_all_devices(self.rm)
            self._closed = True
        return {"status": "closed"}

    # -- setpoints -----------------------------------------------------

    def set_offset(self, offset_v: float) -> dict:
        bounds.check_range("offset", offset_v, bounds.OFFSET_MIN_V, bounds.OFFSET_MAX_V)
        self.open_instruments()
        with self._lock:
            try:
                lia = self._lia
                assert lia is not None
                lia.set_offset(offset_v)
                readback = lia.get_offset()
            except Exception as exc:
                raise InstrumentIOError("LIA", "set_offset", exc) from exc
        self._note_event(f"offset -> {offset_v:g}V")
        return {"offset_v": readback}

    def _scu_for(self, channel: str) -> "ATE.SCU":
        if channel not in _CHANNEL_TO_SCU_TAG:
            raise ValueError(f"channel must be 'SCU1' or 'SCU2', got {channel!r}")
        scu = self._scu1 if channel == "SCU1" else self._scu2
        assert scu is not None
        return scu

    def set_drain_voltage(self, channel: str, voltage_v: float) -> dict:
        """Set the SCU voltage-source level for ``channel`` and validate the
        resulting drain current/voltage. On violation, rolls back to the
        last known-good voltage and raises."""
        self.open_instruments()
        with self._lock:
            scu = self._scu_for(channel)
            previous_voltage = self._last_good_voltage[channel]
            try:
                scu.set_source_function(
                    ATE.SourceFunction.VOLTAGE,
                    bounds.SCU_CURRENT_COMPLIANCE_A,
                    channel=1,
                )
                scu.set_voltage(voltage_v, channel=1)
                scu.enable_output(channel=1)
                time.sleep(bounds.SETTLE_AFTER_SETPOINT_S)
                iscu = scu.measure_current(channel=1)
            except Exception as exc:
                raise InstrumentIOError(channel, "set_drain_voltage", exc) from exc

            vd = voltage_v - bounds.SERIES_RESISTANCE_OHM * iscu

            def _rollback() -> None:
                scu.set_voltage(previous_voltage, channel=1)
                self._last_good_voltage[channel] = previous_voltage

            if vd <= bounds.VD_MIN_V:
                _rollback()
                raise DrainVoltageError(channel, vd, bounds.VD_MIN_V)
            if not (bounds.SCU_CURRENT_MIN_A <= iscu <= bounds.SCU_CURRENT_MAX_A):
                _rollback()
                raise OutOfRangeError(
                    f"{channel}_current",
                    iscu,
                    bounds.SCU_CURRENT_MIN_A,
                    bounds.SCU_CURRENT_MAX_A,
                )

            self._last_good_voltage[channel] = voltage_v

        self._note_event(
            f"{channel} voltage -> {voltage_v:g}V (Iscu={iscu:g}A, Vd={vd:g}V)"
        )
        return {
            "channel": channel,
            "voltage_v": voltage_v,
            "current_a": iscu,
            "vd_v": vd,
        }

    def read_drain_state(self, channel: str) -> dict:
        self.open_instruments()
        with self._lock:
            scu = self._scu_for(channel)
            try:
                vscu = scu.get_voltage(channel=1)
                iscu = scu.measure_current(channel=1)
            except Exception as exc:
                raise InstrumentIOError(channel, "read_drain_state", exc) from exc
        vd = vscu - bounds.SERIES_RESISTANCE_OHM * iscu
        current_ok = bounds.SCU_CURRENT_MIN_A <= iscu <= bounds.SCU_CURRENT_MAX_A
        return {
            "channel": channel,
            "vscu_v": vscu,
            "iscu_a": iscu,
            "vd_v": vd,
            "current_ok": current_ok,
            "vd_ok": vd > bounds.VD_MIN_V,
        }

    def set_heater_voltage(self, channel: int, voltage_v: float) -> dict:
        if channel not in (1, 3):
            raise ValueError(f"channel must be 1 or 3, got {channel!r}")
        bounds.check_range(
            "heater_voltage", voltage_v, bounds.HEATER_MIN_V, bounds.HEATER_MAX_V
        )
        self.open_instruments()
        with self._lock:
            try:
                psu = self._psu
                assert psu is not None
                psu.set_voltage(channel, voltage_v)
                psu.enable_output(channel)
                readback = psu.get_output_voltage(channel)
            except Exception as exc:
                raise InstrumentIOError("PSU", "set_heater_voltage", exc) from exc
        self._note_event(f"heater ch{channel} -> {voltage_v:g}V")
        return {"channel": channel, "voltage_v": readback}

    def zero_phase(
        self,
        n_samples: int = 30,
        sample_interval: float = 2.0,
        sigma_tolerance_deg: float = 0.2,
        max_iterations: int = 5,
    ) -> dict:
        self.open_instruments()
        with self._lock:
            lia = self._lia
            assert lia is not None
            try:
                result = sigma_phase_zero(
                    lia,
                    n_samples=n_samples,
                    sample_interval=sample_interval,
                    sigma_tolerance_deg=sigma_tolerance_deg,
                    max_iterations=max_iterations,
                )
            except Exception as exc:
                if hasattr(exc, "code"):
                    raise
                raise InstrumentIOError("LIA", "zero_phase", exc) from exc
        self._note_event(f"auto-phase converged (sigma={result['sigma_deg']:.4f}deg)")
        return result

    # -- readouts ------------------------------------------------------

    def _snap_r_theta(self) -> tuple[float, float]:
        """Take one LIA snap and return (R, theta); assumes ``self._lock`` held."""
        lia = self._lia
        assert lia is not None
        import numpy as np

        x, y, r = lia.snap(0, 1, 2)  # 0=X, 1=Y, 2=R
        theta = float(np.degrees(np.arctan2(y, x)))
        return r, theta

    def read_r(
        self,
        n_samples: int = 1,
        sample_interval: float = 0.5,
        force_fresh_snap: bool = False,
    ) -> dict:
        self.open_instruments()
        if (
            not force_fresh_snap
            and self._monitor is not None
            and self._monitor.status()["running"]
        ):
            status = self._monitor.status()
            return {
                "r_v": status["latest_r_v"],
                "theta_deg": status["latest_theta_deg"],
                "n_samples": 1,
                "sigma_r_v": None,
                "source": "monitor",
            }
        import numpy as np

        with self._lock:
            try:
                r_samples = []
                theta_samples = []
                for i in range(n_samples):
                    r, theta = self._snap_r_theta()
                    r_samples.append(r)
                    theta_samples.append(theta)
                    if i < n_samples - 1:
                        time.sleep(sample_interval)
            except Exception as exc:
                raise InstrumentIOError("LIA", "read_r", exc) from exc
        return {
            "r_v": float(np.mean(r_samples)),
            "theta_deg": float(np.mean(theta_samples)),
            "n_samples": n_samples,
            "sigma_r_v": float(np.std(r_samples)) if n_samples > 1 else None,
            "source": "fresh_snap",
        }

    # -- continuous monitoring ------------------------------------------

    def start_monitoring(
        self,
        sample_interval: float = 1.0,
        drift_window_s: float = 60.0,
        label: str | None = None,
    ) -> dict:
        self.open_instruments()
        with self._lock:
            if self._monitor is not None and self._monitor.status()["running"]:
                raise MonitorStateError("a monitor is already running")
            assert self._lia is not None and self._scu1 is not None
            assert self._scu2 is not None and self._psu is not None

            self.snapshot.devices.clear()
            self.snapshot_lia(self._lia)
            self.snapshot_scu(self._scu1, label="SCU1")
            self.snapshot_scu(self._scu2, label="SCU2")
            for ch in (1, 3):
                self.snapshot_psu(self._psu, channel=ch)

            stem = label or datetime.now().strftime("%H%M%S")
            csv_path = os.path.join(self.results_dir, f"monitor_{stem}.csv")

            def _read_sample():
                with self._lock:
                    return self._snap_r_theta()

            monitor = ContinuousMonitor(
                _read_sample,
                csv_path,
                self.snapshot,
                sample_interval=sample_interval,
                drift_window_s=drift_window_s,
            )
            monitor.start()
            self._monitor = monitor
        return {"status": "started", "csv_path": csv_path}

    def monitor_status(self) -> dict:
        if self._monitor is None:
            raise MonitorStateError("no monitor has been started")
        return self._monitor.status()

    def note_event(self, note: str) -> dict:
        if self._monitor is None or not self._monitor.status()["running"]:
            raise MonitorStateError("no monitor is running to attach a note to")
        row_index = self._monitor.add_event(note)
        return {"row_index": row_index}

    def stop_monitoring(self, plot: bool = True) -> dict:
        if self._monitor is None:
            raise MonitorStateError("no monitor has been started")
        result = self._monitor.stop()
        plot_path = None
        if plot:
            from plotting import plot_r_monitor_session

            t, r, theta, events = self._monitor.buffer()
            if t:
                plot_path = plot_r_monitor_session(
                    self._monitor.csv_path,
                    t,
                    r,
                    theta,
                    events,
                    self._monitor.drift_window_s,
                )
        result["plot_path"] = plot_path
        return result

    def plot_monitor_session(self) -> dict:
        if self._monitor is None:
            raise MonitorStateError("no monitor has been started")
        from plotting import plot_r_monitor_session

        t, r, theta, events = self._monitor.buffer()
        if not t:
            raise MonitorStateError("monitor has no samples yet")
        plot_path = plot_r_monitor_session(
            self._monitor.csv_path, t, r, theta, events, self._monitor.drift_window_s
        )
        return {"plot_path": plot_path}

    # -- misc ------------------------------------------------------------

    def snapshot_state(self) -> dict:
        self.open_instruments()
        with self._lock:
            lia = self._lia
            psu = self._psu
            assert lia is not None and psu is not None
            offset_v = lia.get_offset()
            scu1_state = self.read_drain_state("SCU1")
            scu2_state = self.read_drain_state("SCU2")
            heater1_v = psu.get_output_voltage(1)
            heater3_v = psu.get_output_voltage(3)
        return {
            "offset_v": offset_v,
            "scu1": scu1_state,
            "scu2": scu2_state,
            "heater_ch1_v": heater1_v,
            "heater_ch3_v": heater3_v,
        }

    def _note_event(self, note: str) -> None:
        if self._monitor is not None and self._monitor.status()["running"]:
            self._monitor.add_event(note)
