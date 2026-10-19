"""
Plotting for NoiseSpectrumSetup: time-domain record + noise PSD.
"""

import csv
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import medfilt

from .lia_analysis import _output_path

logger = logging.getLogger(__name__)


class NoiseSpectrumCompiler:
    """Reads a ``noise_spectrum.csv`` written by ``NoiseSpectrumSetup`` and
    plots the amplitude spectral density (log-log) over ``[f_min, f_max]``.

    The CSV may start with a settings preamble (device label rows such as
    ``SCU1``/``LIA``/``Scope`` followed by ``setting,value`` rows — the same
    convention ``LIASnapDigest`` parses for other experiments' CSVs) before
    the ``frequency_hz,psd_v2_per_hz,asd_v_per_sqrt_hz`` header; older CSVs
    with no preamble (header is the first row) are read the same way.

    ``amplifier_gain`` is the external (SR560) amplifier gain (V/V) in effect
    when the capture was taken. The plotted curve is always input-referred
    (the raw, amplifier-output-measured ASD divided by the gain) — the
    equivalent noise at the differential amplifier's input / device side.

    When ``show_trendline`` is set, a red-dashed "device noise" trendline is
    overlaid: a rolling median filter over ``trendline_window_hz`` (converted
    to an odd bin count via the Welch frequency spacing), which rejects
    narrow spikes (mains harmonics only occupy 1-2 bins) while tracking the
    broad 1/f + white-noise trend. Purely cosmetic — never affects the saved
    data.
    """

    def __init__(
        self, csv_path: str, f_min: float, f_max: float, amplifier_gain: float = 1.0,
        show_trendline: bool = True, trendline_window_hz: float = 10.0,
    ):
        self.csv_path = Path(csv_path).resolve()
        self.f_min = f_min
        self.f_max = f_max
        self.amplifier_gain = amplifier_gain
        self.show_trendline = show_trendline
        self.trendline_window_hz = trendline_window_hz

        freq: list[float] = []
        asd: list[float] = []
        in_data = False
        with open(self.csv_path, newline="") as f:
            for row in csv.reader(f):
                if not row:
                    continue
                if not in_data:
                    if row[0].strip() == "frequency_hz":
                        in_data = True
                    continue
                freq.append(float(row[0]))
                asd.append(float(row[2]))
        if not in_data:
            raise ValueError(f"{csv_path}: no 'frequency_hz' header found")
        if not freq:
            raise ValueError(f"no rows in {csv_path}")
        self.freq = np.array(freq)
        self.asd = np.array(asd)

    def compile(self) -> str:
        mask = (self.freq >= self.f_min) & (self.freq <= self.f_max)
        freq = self.freq[mask]
        asd = self.asd[mask] / self.amplifier_gain

        fig, ax = plt.subplots(figsize=(8, 5.5))
        label = "measured" if self.show_trendline else None
        ax.loglog(freq, asd, "-", lw=1.2, label=label)
        if self.show_trendline and freq.size > 1:
            bin_spacing = float(np.median(np.diff(freq)))
            kernel = max(1, int(round(self.trendline_window_hz / bin_spacing)))
            if kernel % 2 == 0:
                kernel += 1
            kernel = min(kernel, freq.size if freq.size % 2 == 1 else freq.size - 1)
            trend = medfilt(asd, kernel_size=kernel)
            ax.loglog(freq, trend, "r--", lw=1.5, label="device noise trend")
            ax.legend(loc="best", fontsize=8)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Differential readout noise spectrum (V/√Hz)")
        ax.yaxis.tick_left()
        ax.yaxis.set_label_position("left")
        ax.spines["right"].set_visible(False)
        ax.set_xlim(self.f_min, self.f_max)
        ax.grid(True, which="both", alpha=0.3)

        out = _output_path(self.csv_path, "_psd.png")
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Plot saved to: {out}")
        return str(out)
