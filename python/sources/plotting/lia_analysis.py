import csv
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

from .plot_compiler import PlotCompiler

logger = logging.getLogger(__name__)

_PARAM_KEYS = ("freq", "offset", "ampitude", "i_bias", "sr560_amp")
_PARAM_UNITS = {"freq": "Hz", "offset": "V", "ampitude": "V",
                "i_bias": "A", "sr560_amp": "x"}

# Statistics plotted by the sweep scatter, in (key, axis label) order.
_SWEEP_STATS = (
    ("avg_X", "Average X (V)"),
    ("avg_Y", "Average Y (V)"),
    ("avg_R", "Average R (V)"),
    ("rmse_X", "X RMSE (V)"),
    ("rmse_Y", "Y RMSE (V)"),
    ("rmse_R", "R RMSE (V)"),
)


def _output_path(csv_path: Path, suffix: str) -> Path:
    """Map Results/.../foo.csv -> Plots/.../foo<suffix>."""
    parts = csv_path.parts
    if "Results" not in parts:
        return csv_path.with_name(csv_path.stem + suffix)
    results_idx = parts.index("Results")
    rel = Path(*parts[results_idx + 1:])
    project_root = csv_path
    for _ in range(len(parts) - results_idx):
        project_root = project_root.parent
        if (project_root / "Results").exists():
            break
    return project_root / "Plots" / rel.with_name(csv_path.stem + suffix)


class LIASnapDigest:
    """Digest a single SR860 snap CSV: avg X/Y/R, RMSE of X/Y, and phase theta.

    The CSV starts with a setup snapshot written as nested rows (a device label
    row such as ``LIA`` / ``PSU[ch1]`` / ``SCU1[ch1]`` followed by ``setting,value``
    rows), then a ``time,X,Y,R`` header and the measurement rows. Only X, Y and R
    are recorded by the SR860; the phase theta is reconstructed as atan2(Y, X).

    When ``baseline`` is set, the R trace is fit to a linear drift model and the
    estimated drift rate is reported and overlaid on the plot.
    """

    def __init__(self, csv_path: str, baseline: bool = False):
        self.csv_path = Path(csv_path).resolve()
        self.baseline = baseline
        # setup snapshot: device label -> {setting: raw string value}
        self.setup: dict[str, dict[str, str]] = {}
        self._t: np.ndarray | None = None
        self._x: np.ndarray | None = None
        self._y: np.ndarray | None = None
        self._r: np.ndarray | None = None
        self._theta: np.ndarray | None = None
        self._parse()

    def _parse(self) -> None:
        setup: dict[str, dict[str, str]] = {}
        current_device: str | None = None
        data_rows: list[list[str]] = []
        in_data = False
        with open(self.csv_path, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                if not in_data:
                    first = row[0].strip()
                    if first.lower() == "time":
                        in_data = True
                        continue
                    rest = [c.strip() for c in row[1:]]
                    if not any(rest):
                        # device label row, e.g. "LIA,,," or "PSU[ch1],,,"
                        current_device = first
                        setup.setdefault(current_device, {})
                    elif current_device is not None:
                        # "setting,value" row belonging to the current device
                        setup[current_device][first] = rest[0]
                    continue
                if len(row) >= 4:
                    data_rows.append(row)
        if not in_data:
            raise ValueError(f"{self.csv_path}: no 'time,X,Y,R' header found")

        arr = np.array([[float(c) for c in r[:4]] for r in data_rows])
        self.setup = setup
        self._t = arr[:, 0]
        self._x = arr[:, 1]
        self._y = arr[:, 2]
        self._r = arr[:, 3]
        # SR860 only reports 3 params at a time (X, Y, R here); reconstruct phase.
        self._theta = np.degrees(np.arctan2(self._y, self._x))

    def _setting(self, device: str, key: str) -> float | None:
        """Return a numeric setup setting, or None if absent/non-numeric."""
        try:
            return float(self.setup[device][key])
        except (KeyError, ValueError, TypeError):
            return None

    def _drift_fit(self) -> tuple[float, float]:
        """Linear least-squares fit of R vs time; return (slope [V/s], intercept [V])."""
        assert self._t is not None and self._r is not None
        slope, intercept = np.polyfit(self._t, self._r, 1)
        return float(slope), float(intercept)

    def digest(self) -> dict:
        assert (self._x is not None and self._y is not None
                and self._r is not None and self._theta is not None)
        rmse_x = float(np.std(self._x))
        rmse_y = float(np.std(self._y))
        slope, intercept = self._drift_fit()
        return {
            "avg_X": float(np.mean(self._x)),
            "avg_Y": float(np.mean(self._y)),
            "avg_R": float(np.mean(self._r)),
            "avg_theta": float(np.mean(self._theta)),
            "rmse_X": rmse_x,
            "rmse_Y": rmse_y,
            "rmse_R": float(np.hypot(rmse_x, rmse_y)),
            "xcorr_XY": self._xcorr(),
            "drift_R_slope": slope,
            "drift_R_intercept": intercept,
            "params": dict(self.params),
        }

    @property
    def params(self) -> dict[str, float]:
        """Flat map of the setup values of interest, for reporting/textbox."""
        pairs = {
            "freq": ("LIA", "frequency_Hz"),
            "psu_ch1_V": ("PSU[ch1]", "voltage_V"),
            "psu_ch3_V": ("PSU[ch3]", "voltage_V"),
            "smu1_V": ("SCU1[ch1]", "voltage_V"),
            "smu2_V": ("SCU2[ch1]", "voltage_V"),
        }
        out: dict[str, float] = {}
        for name, (device, key) in pairs.items():
            v = self._setting(device, key)
            if v is not None:
                out[name] = v
        return out

    def _xcorr(self) -> float:
        """Pearson cross-correlation coefficient of the X and Y time traces."""
        assert self._x is not None and self._y is not None
        if np.std(self._x) == 0 or np.std(self._y) == 0:
            return float("nan")
        return float(np.corrcoef(self._x, self._y)[0, 1])

    def compile(self) -> str:
        d = self.digest()
        out = _output_path(self.csv_path, "_digest.csv")
        out.parent.mkdir(parents=True, exist_ok=True)
        keys = ["freq", "psu_ch1_V", "psu_ch3_V", "smu1_V", "smu2_V"]
        stat_keys = [
            "avg_X", "avg_Y", "avg_R", "avg_theta",
            "rmse_X", "rmse_Y", "rmse_R", "xcorr_XY",
            "drift_R_slope", "drift_R_intercept",
        ]
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(keys + stat_keys)
            row = [d["params"].get(k, "") for k in keys] + [d[k] for k in stat_keys]
            w.writerow(row)

        print(f"Digest for {self.csv_path.name}:")
        for k in keys:
            if k in d["params"]:
                print(f"  {k:18s} = {d['params'][k]}")
        for k in stat_keys:
            print(f"  {k:18s} = {d[k]:.6g}")
        return str(out)

    def _setup_textbox_lines(self) -> list[str]:
        """Formatted table lines for the setup-settings textbox."""
        rows = [
            ("LIA freq", self.params.get("freq"), "Hz"),
            ("PSU ch1", self.params.get("psu_ch1_V"), "V"),
            ("PSU ch3", self.params.get("psu_ch3_V"), "V"),
            ("SMU1", self.params.get("smu1_V"), "V"),
            ("SMU2", self.params.get("smu2_V"), "V"),
        ]
        lines = ["setup:"]
        for label, val, unit in rows:
            val_str = f"{val:.4g} {unit}" if val is not None else "n/a"
            lines.append(f"  {label:9s} {val_str}")
        return lines

    def plot_timeseries(self) -> str:
        """Plot X, Y, R and phase theta versus time into a single PNG.

        A textbox in the top-left lists the key setup settings. When ``baseline``
        is set, a linear drift fit of R is overlaid with its estimated drift rate.
        """
        assert (
            self._t is not None and self._x is not None and self._y is not None
            and self._r is not None and self._theta is not None
        )
        out = _output_path(self.csv_path, "_timeseries.png")
        out.parent.mkdir(parents=True, exist_ok=True)

        traces = [
            (self._x, "X (V)"),
            (self._y, "Y (V)"),
            (self._r, "R (V)"),
            (self._theta, "θ = atan2(Y, X) (deg)"),
        ]
        fig, axes = plt.subplots(len(traces), 1, sharex=True, figsize=(8, 11))
        fig.suptitle(self.csv_path.stem)

        fmt = ticker.FuncFormatter(PlotCompiler._smart_fmt)
        for ax, (data, label) in zip(axes, traces):
            ax.plot(self._t, data, linewidth=0.8)
            ax.set_ylabel(label)
            ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
            ax.yaxis.set_major_formatter(fmt)

        # Setup-settings table, top-left of the first (X) subplot.
        axes[0].text(
            0.02, 0.97, "\n".join(self._setup_textbox_lines()),
            transform=axes[0].transAxes, va="top", ha="left",
            fontsize=8, family="monospace",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
        )

        # Baseline drift analysis: linear fit of R vs time.
        if self.baseline:
            ax_r = axes[2]
            slope, intercept = self._drift_fit()
            ax_r.plot(self._t, slope * self._t + intercept, color="red",
                      linewidth=1.2, linestyle="--", label="linear drift fit")
            total = slope * (self._t[-1] - self._t[0])
            txt = (f"R(t) = {slope:+.3e}·t + {intercept:.6g}\n"
                   f"drift = {slope:+.3e} V/s ({slope * 3600:+.3e} V/hr)\n"
                   f"ΔR over run = {total:+.3e} V")
            ax_r.text(
                0.98, 0.05, txt, transform=ax_r.transAxes, va="bottom", ha="right",
                fontsize=8, family="monospace", color="darkred",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
            )
            ax_r.legend(loc="upper right", fontsize=8)

        axes[-1].set_xlabel("Time (s)")
        fig.tight_layout()
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return str(out)


class LIASweepScatterCompiler:
    """Scatter plot of digest stats across many snap CSVs varying one parameter."""

    def __init__(self, csv_paths: list[str], sweep_param: str,
                 out_name: str | None = None):
        if sweep_param not in _PARAM_KEYS:
            raise ValueError(
                f"sweep_param must be one of {_PARAM_KEYS}, got {sweep_param!r}"
            )
        if len(csv_paths) < 2:
            raise ValueError("need at least 2 CSVs to plot a sweep")
        self.csv_paths = [Path(p).resolve() for p in csv_paths]
        self.sweep_param = sweep_param
        self.out_name = out_name

    def compile(self) -> str:
        digests = [LIASnapDigest(str(p)).digest() for p in self.csv_paths]

        if any(self.sweep_param not in d["params"] for d in digests):
            missing = [p.name for p, d in zip(self.csv_paths, digests)
                       if self.sweep_param not in d["params"]]
            raise ValueError(f"sweep param {self.sweep_param!r} missing in: {missing}")

        sweep_vals = [d["params"][self.sweep_param] for d in digests]

        other = [k for k in _PARAM_KEYS if k != self.sweep_param]
        for k in other:
            vals = {d["params"].get(k) for d in digests}
            if len(vals) > 1:
                logger.warning(
                    "param %r varies across files (%s); expected fixed for %s sweep",
                    k,
                    sorted(v for v in vals if v is not None),
                    self.sweep_param,
                )

        order = np.argsort(sweep_vals)
        sweep_vals = [sweep_vals[i] for i in order]
        digests = [digests[i] for i in order]

        for val, d in zip(sweep_vals, digests):
            logger.info(
                "%s = %g: X-Y cross-correlation = %.6g",
                self.sweep_param, val, d["xcorr_XY"],
            )

        fig, axes = plt.subplots(len(_SWEEP_STATS), 1, sharex=True, figsize=(8, 12))
        fig.suptitle(f"{self.sweep_param} sweep ({len(digests)} files)")

        fmt = ticker.FuncFormatter(PlotCompiler._smart_fmt)
        for ax, (key, label) in zip(axes, _SWEEP_STATS):
            ax.scatter(sweep_vals, [d[key] for d in digests])
            ax.set_ylabel(label)
            ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
            ax.yaxis.set_major_formatter(fmt)

        unit = _PARAM_UNITS.get(self.sweep_param, "")
        xlabel = f"{self.sweep_param} ({unit})" if unit else self.sweep_param
        axes[-1].set_xlabel(xlabel)
        axes[-1].xaxis.set_major_formatter(fmt)

        fig.tight_layout()

        stem = self.out_name or f"{self.sweep_param}_sweep"
        anchor = self.csv_paths[0]
        out = _output_path(anchor, "").parent / f"{stem}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return str(out)


class LIADiffSweepScatterCompiler:
    """Scatter of the (signal - baseline) difference of digest stats over a sweep.

    Each baseline (e.g. nogas) CSV is paired with the signal (e.g. gas) CSV at
    the same sweep-parameter value; their digest results (average, RMSE, ...) are
    subtracted and the difference is plotted with the same layout as
    ``LIASweepScatterCompiler``.
    """

    def __init__(self, baseline_paths: list[str], signal_paths: list[str],
                 sweep_param: str, out_name: str | None = None):
        if sweep_param not in _PARAM_KEYS:
            raise ValueError(
                f"sweep_param must be one of {_PARAM_KEYS}, got {sweep_param!r}"
            )
        if len(baseline_paths) < 2 or len(signal_paths) < 2:
            raise ValueError("need at least 2 baseline and 2 signal CSVs")
        self.baseline_paths = [Path(p).resolve() for p in baseline_paths]
        self.signal_paths = [Path(p).resolve() for p in signal_paths]
        self.sweep_param = sweep_param
        self.out_name = out_name

    def _digests_by_value(self, paths: list[Path]) -> dict[float, dict]:
        by_value: dict[float, dict] = {}
        for p in paths:
            d = LIASnapDigest(str(p)).digest()
            if self.sweep_param not in d["params"]:
                raise ValueError(
                    f"sweep param {self.sweep_param!r} missing in: {p.name}"
                )
            val = d["params"][self.sweep_param]
            if val in by_value:
                names = [p.name for p in paths]
                raise ValueError(
                    f"duplicate {self.sweep_param}={val:g} among {names}"
                )
            by_value[val] = d
        return by_value

    def compile(self) -> str:
        baseline = self._digests_by_value(self.baseline_paths)
        signal = self._digests_by_value(self.signal_paths)

        common = sorted(set(baseline) & set(signal))
        only_base = set(baseline) - set(signal)
        only_sig = set(signal) - set(baseline)
        for label, vals in (("baseline", only_base), ("signal", only_sig)):
            if vals:
                logger.warning(
                    "%s has %s value(s) with no match in the other group: %s",
                    label, self.sweep_param, sorted(vals),
                )
        if len(common) < 2:
            raise ValueError(
                f"need at least 2 matched {self.sweep_param} values, got {common}"
            )

        diffs = [
            {k: signal[v][k] - baseline[v][k] for k, _ in _SWEEP_STATS}
            for v in common
        ]

        for val, d in zip(common, diffs):
            logger.info(
                "%s = %g: signal-baseline avg_R = %.6g, rmse_R = %.6g",
                self.sweep_param, val, d["avg_R"], d["rmse_R"],
            )

        fig, axes = plt.subplots(len(_SWEEP_STATS), 1, sharex=True, figsize=(8, 12))
        fig.suptitle(
            f"{self.sweep_param} sweep difference "
            f"(signal - baseline, {len(common)} pairs)"
        )

        fmt = ticker.FuncFormatter(PlotCompiler._smart_fmt)
        for ax, (key, label) in zip(axes, _SWEEP_STATS):
            ax.scatter(common, [d[key] for d in diffs])
            ax.axhline(0, color="0.6", linewidth=0.8, linestyle="--")
            ax.set_ylabel(f"Δ {label}")
            ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
            ax.yaxis.set_major_formatter(fmt)

        unit = _PARAM_UNITS.get(self.sweep_param, "")
        xlabel = f"{self.sweep_param} ({unit})" if unit else self.sweep_param
        axes[-1].set_xlabel(xlabel)
        axes[-1].xaxis.set_major_formatter(fmt)

        fig.tight_layout()

        stem = self.out_name or f"{self.sweep_param}_diff_sweep"
        anchor = self.signal_paths[0]
        out = _output_path(anchor, "").parent / f"{stem}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return str(out)
