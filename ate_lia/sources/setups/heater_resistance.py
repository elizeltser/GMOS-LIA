"""
Heater resistance measurement: linear I-V fit of PSU heater channels.
"""

import csv
import logging
import os
import time
from datetime import datetime

import ATE
import numpy as np
from config import ATEConfig, HeaterResistanceConfig
from plotting import HeaterResistanceCompiler
from plotting.lia_analysis import heater_resistance_fits

from .setup_base import SetupBase

logger = logging.getLogger(__name__)

_POINT_FIELDS = [
    "repeat", "channel", "set_voltage", "mean_voltage", "mean_current",
    "std_current", "sem_current", "n_samples",
]


class HeaterResistanceSetup(SetupBase):
    """Estimate PSU ch1/ch3 heater resistances.

    Sweeps each channel through ``heater_voltages``, averaging ``n_samples``
    V/I readings (``sample_interval`` apart) per point, repeats the whole sweep
    ``n_repeats`` times, writes a raw CSV plus a fit summary, and plots the
    linear fit with R^2 and error lines. ESD/fan protection is on via
    ``setup_ate``; no other instrument is used.
    """

    def __init__(self, output_name: str = None, ate_config: ATEConfig = None,  # type: ignore
                 config: HeaterResistanceConfig = None) -> None:  # type: ignore
        super().__init__(output_name=output_name, ate_config=ate_config)
        self.config: HeaterResistanceConfig = config or HeaterResistanceConfig()

    def _measure_point(
        self, psu: "ATE.PSU", ch: int
    ) -> tuple[float, float, float, float, float]:
        """Return mean V, mean I, std I, sem I, mean actual sample interval."""
        cfg = self.config
        vs, is_ = [], []
        t0 = time.perf_counter()
        for k in range(cfg.n_samples):
            if k:
                time.sleep(cfg.sample_interval)
            vs.append(psu.get_output_voltage(ch))
            is_.append(psu.get_output_current(ch))
        dt = (time.perf_counter() - t0) / max(cfg.n_samples - 1, 1)
        std = float(np.std(is_, ddof=1)) if len(is_) > 1 else 0.0
        return (float(np.mean(vs)), float(np.mean(is_)), std,
                std / np.sqrt(len(is_)), dt)

    @SetupBase.setup_ate
    def run(self) -> None:
        cfg = self.config
        if not cfg.heater_voltages:
            raise ValueError(
                "HeaterResistanceSetup requires at least one heater voltage"
            )
        if not cfg.channels or not set(cfg.channels) <= {1, 3}:
            raise ValueError("channels must be a non-empty subset of [1, 3]")
        if cfg.n_samples < 1 or cfg.n_repeats < 1:
            raise ValueError("n_samples and n_repeats must be >= 1")

        stem = cfg.session_folder or f"heater_resistance_{datetime.now():%Y%m%d_%H%M%S}"
        out_dir = os.path.join(self.results_dir, stem)
        os.makedirs(out_dir, exist_ok=True)
        csv_path = os.path.join(out_dir, "heater_resistance.csv")
        logger.info(f"Starting HeaterResistanceSetup -> {out_dir}")

        rows: list[dict] = []
        intervals: list[float] = []
        psu = self.open_no_reset(ATE.PSU(rm=self.rm))
        try:
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=_POINT_FIELDS)
                writer.writeheader()
                for rep in range(1, cfg.n_repeats + 1):
                    for ch in cfg.channels:
                        logger.info(f"--- repeat {rep}/{cfg.n_repeats}, ch{ch} ---")
                        psu.set_current(ch, cfg.current_limit)
                        psu.set_voltage(ch, 0.0)
                        psu.enable_output(ch)
                        for v in cfg.heater_voltages:
                            psu.set_voltage(ch, v)
                            time.sleep(cfg.settle)
                            mv, mi, std, sem, dt = self._measure_point(psu, ch)
                            intervals.append(dt)
                            row = {
                                "repeat": rep, "channel": ch, "set_voltage": v,
                                "mean_voltage": mv, "mean_current": mi,
                                "std_current": std, "sem_current": sem,
                                "n_samples": cfg.n_samples,
                            }
                            writer.writerow(row)
                            f.flush()
                            rows.append(row)
                            logger.info(f"ch{ch} V={mv:.4f} I={mi * 1e3:.3f}mA")
                            if mi >= 0.95 * cfg.current_limit:
                                logger.warning(
                                    "Near current limit; stopping this sweep"
                                )
                                break
                        psu.set_voltage(ch, 0.0)
                    if rep < cfg.n_repeats:
                        time.sleep(cfg.repeat_wait)
        finally:
            for ch in cfg.channels:
                psu.set_voltage(ch, 0.0)
            psu.resource.close()

        logger.info(f"Mean actual sample interval: {np.mean(intervals) * 1e3:.2f} ms "
                    f"(requested {cfg.sample_interval * 1e3:.2f} ms)")
        fits = heater_resistance_fits(rows)
        with open(os.path.join(out_dir, "fit_summary.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["channel", "resistance_ohm", "intercept_a", "r2", "mse_a2"])
            for ch, fit in fits.items():
                w.writerow(
                    [ch, fit["resistance"], fit["intercept"], fit["r2"], fit["mse"]]
                )
                logger.info(f"ch{ch}: R={fit['resistance']:.1f} ohm, "
                            f"R^2={fit['r2']:.4f}, MSE={fit['mse']:.3e} A^2")

        for path in HeaterResistanceCompiler(csv_path).compile():
            logger.info(f"Plot saved to: {path}")
        logger.info("HeaterResistanceSetup complete.")
