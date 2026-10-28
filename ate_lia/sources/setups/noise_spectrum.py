"""
Noise spectrum measurement: capture the differential-amplifier output on the
scope and compute its noise power/amplitude spectral density.
"""

import csv
import logging
import os
import time
from datetime import datetime

import ATE
import numpy as np
from config import ATEConfig, NoiseSpectrumConfig
from plotting.noise_spectrum import NoiseSpectrumCompiler
from scipy.signal import welch

from .lia_setup import LIAMeasurementSetup
from .setup_base import SetupBase

logger = logging.getLogger(__name__)


class NoiseSpectrumSetup(SetupBase):
    """Bias the device (SCU1/SCU2 drain, LIA gate offset), digitize a single
    time-domain record of the differential-amplifier output on the scope,
    then compute its noise PSD/ASD via Welch's method over ``[config.f_min,
    config.f_max]``.

    Writes ``timeseries.csv`` (raw ``time_s``/``voltage_v``) and
    ``noise_spectrum.csv`` (a settings preamble — SCU1/SCU2/LIA/Scope/gain —
    followed by ``frequency_hz``/``psd_v2_per_hz``/``asd_v_per_sqrt_hz``),
    plus a log-log ASD plot (optionally with a red-dashed de-spiked
    "device noise" trendline, see ``NoiseSpectrumConfig.show_trendline``).
    ESD/fan protection (and heaters, if configured via
    ``ATEConfig.heater1``/``heater3``) are enabled via ``setup_ate`` at the
    start; the whole setup (LIA, SCU1/SCU2, and all 4 PSU channels — ESD,
    fan, heaters) is de-energized at the end via
    ``LIAMeasurementSetup._shutdown_all_devices``, even on failure.
    """

    def __init__(self, output_name: str = None, ate_config: ATEConfig = None,  # type: ignore
                 config: NoiseSpectrumConfig = None) -> None:  # type: ignore
        super().__init__(output_name=output_name, ate_config=ate_config)
        self.config: NoiseSpectrumConfig = config or NoiseSpectrumConfig()

    @SetupBase.setup_ate
    def run(self) -> None:
        cfg = self.config
        if cfg.f_min <= 0 or cfg.f_max <= cfg.f_min:
            raise ValueError("require 0 < f_min < f_max")
        if cfg.sample_rate_hz < 2 * cfg.f_max:
            raise ValueError(
                f"sample_rate_hz ({cfg.sample_rate_hz}) must be >= 2 * f_max "
                f"({2 * cfg.f_max}) to resolve the requested band"
            )

        stem = cfg.session_folder or f"noise_spectrum_{datetime.now():%Y%m%d_%H%M%S}"
        out_dir = os.path.join(self.results_dir, stem)
        os.makedirs(out_dir, exist_ok=True)
        logger.info(f"Starting NoiseSpectrumSetup -> {out_dir}")

        n_points = int(round(cfg.duration_s * cfg.sample_rate_hz))

        try:
            self._run_capture(cfg, out_dir, n_points)
        finally:
            LIAMeasurementSetup._shutdown_all_devices(self.rm)
        logger.info("NoiseSpectrumSetup complete.")

    def _run_capture(
        self, cfg: NoiseSpectrumConfig, out_dir: str, n_points: int
    ) -> None:
        with ATE.LIA(rm=self.rm) as lia, ATE.SCU("SCU1", rm=self.rm) as scu1, \
                ATE.SCU("SCU2", rm=self.rm) as scu2:
            lia.set_offset(cfg.gate_voltage)
            lia.set_amplitude(cfg.lia_amplitude)

            scu1.set_source_function(
                ATE.SourceFunction.VOLTAGE, cfg.scu_compliance, channel=1
            )
            scu1.set_voltage(cfg.v_scu1, channel=1)
            scu1.enable_output(channel=1)

            scu2.set_source_function(
                ATE.SourceFunction.VOLTAGE, cfg.scu_compliance, channel=1
            )
            scu2.set_voltage(cfg.v_scu2, channel=1)
            scu2.enable_output(channel=1)

            logger.info(
                f"Biasing device: gate={cfg.gate_voltage}V, "
                f"SCU1={cfg.v_scu1}V, SCU2={cfg.v_scu2}V; "
                f"letting it settle ({cfg.startup_settle:g}s)"
            )
            time.sleep(cfg.startup_settle)

            self.snapshot.add("LIA", {
                "gate_voltage_V": cfg.gate_voltage,
                "amplitude_V": cfg.lia_amplitude,
            })
            self.snapshot_scu(scu1, channel=1, label="SCU1")
            self.snapshot_scu(scu2, channel=1, label="SCU2")

            with ATE.Scope(rm=self.rm) as scope:
                scope.set_channel_display(cfg.channel, True)
                scope.set_channel_coupling(cfg.channel, cfg.coupling)
                scope.set_channel_impedance(cfg.channel, cfg.impedance)
                scope.set_channel_range(cfg.channel, cfg.volts_full_scale)
                scope.set_channel_offset(cfg.channel, cfg.channel_offset)

                scope.set_acquisition_mode(cfg.acquisition_mode)
                scope.set_sample_rate(cfg.sample_rate_hz)
                scope.set_acquisition_points(n_points)
                scope.set_timebase_range(cfg.duration_s)
                scope.set_timebase_position(cfg.duration_s / 2)
                scope.set_trigger_auto_sweep()

                self.snapshot.add("Scope", {
                    "channel": cfg.channel,
                    "coupling": cfg.coupling,
                    "impedance": cfg.impedance,
                    "volts_full_scale": cfg.volts_full_scale,
                    "channel_offset_V": cfg.channel_offset,
                    "acquisition_mode": cfg.acquisition_mode,
                    "requested_sample_rate_Hz": cfg.sample_rate_hz,
                    "requested_points": n_points,
                    "duration_s": cfg.duration_s,
                    "external_amplifier_gain_V_per_V": cfg.amplifier_gain,
                })

                logger.info(
                    f"Digitizing CH{cfg.channel}: {cfg.duration_s}s @ "
                    f"{cfg.sample_rate_hz:.0f} Hz ({n_points} points requested)"
                )
                timeout_ms = int(max(30_000, cfg.duration_s * 1000 * 3))
                scope.digitize(cfg.channel, timeout_ms=timeout_ms)
                t, v = scope.get_waveform(cfg.channel)

        actual_fs = 1.0 / float(np.mean(np.diff(t)))
        logger.info(f"Captured {t.size} points, actual sample rate {actual_fs:.1f} Hz")

        ts_path = os.path.join(out_dir, "timeseries.csv")
        with open(ts_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time_s", "voltage_v"])
            writer.writerows(zip(t, v))
        logger.info(f"Raw time series saved to {ts_path}")

        nperseg = cfg.nperseg or int(actual_fs / cfg.f_min * 2)
        nperseg = max(8, min(nperseg, v.size))
        freq, psd = welch(
            v, fs=actual_fs, window=cfg.window, nperseg=nperseg,
            noverlap=nperseg // 2, scaling="density",
        )
        asd = np.sqrt(psd)

        spec_path = os.path.join(out_dir, "noise_spectrum.csv")
        with open(spec_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(self.snapshot.as_rows(width=3))
            writer.writerow(["frequency_hz", "psd_v2_per_hz", "asd_v_per_sqrt_hz"])
            writer.writerows(zip(freq, psd, asd))
        logger.info(f"Noise spectrum saved to {spec_path}")

        plot_path = NoiseSpectrumCompiler(
            spec_path, cfg.f_min, cfg.f_max, amplifier_gain=cfg.amplifier_gain,
            show_trendline=cfg.show_trendline,
            trendline_window_hz=cfg.trendline_window_hz,
        ).compile()
        logger.info(f"Plot saved to: {plot_path}")
