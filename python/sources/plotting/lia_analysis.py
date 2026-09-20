import csv
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from scipy.optimize import curve_fit

from .plot_compiler import PlotCompiler

logger = logging.getLogger(__name__)


def _linear_drift_fit(t: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Linear least-squares fit of ``y`` vs ``t``; return (slope, intercept)."""
    slope, intercept = np.polyfit(t, y, 1)
    return float(slope), float(intercept)


def _output_path(csv_path: Path, suffix: str) -> Path:
    """Map Results/.../foo.csv -> Plots/.../foo<suffix>."""
    parts = csv_path.parts
    if "Results" not in parts:
        return csv_path.with_name(csv_path.stem + suffix)
    results_idx = parts.index("Results")
    rel = Path(*parts[results_idx + 1 :])
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
        """Linear least-squares fit of R vs time.

        Returns (slope [V/s], intercept [V])."""
        assert self._t is not None and self._r is not None
        return _linear_drift_fit(self._t, self._r)

    def digest(self) -> dict:
        assert (
            self._x is not None
            and self._y is not None
            and self._r is not None
            and self._theta is not None
        )
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
            "avg_X",
            "avg_Y",
            "avg_R",
            "avg_theta",
            "rmse_X",
            "rmse_Y",
            "rmse_R",
            "xcorr_XY",
            "drift_R_slope",
            "drift_R_intercept",
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
            self._t is not None
            and self._x is not None
            and self._y is not None
            and self._r is not None
            and self._theta is not None
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
            0.02,
            0.97,
            "\n".join(self._setup_textbox_lines()),
            transform=axes[0].transAxes,
            va="top",
            ha="left",
            fontsize=8,
            family="monospace",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
        )

        # Baseline drift analysis: linear fit of R vs time.
        if self.baseline:
            ax_r = axes[2]
            slope, intercept = self._drift_fit()
            ax_r.plot(
                self._t,
                slope * self._t + intercept,
                color="red",
                linewidth=1.2,
                linestyle="--",
                label="linear drift fit",
            )
            total = slope * (self._t[-1] - self._t[0])
            txt = (
                f"R(t) = {slope:+.3e}·t + {intercept:.6g}\n"
                f"drift = {slope:+.3e} V/s ({slope * 3600:+.3e} V/hr)\n"
                f"ΔR over run = {total:+.3e} V"
            )
            ax_r.text(
                0.98,
                0.05,
                txt,
                transform=ax_r.transAxes,
                va="bottom",
                ha="right",
                fontsize=8,
                family="monospace",
                color="darkred",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
            )
            ax_r.legend(loc="lower right", fontsize=8)

        axes[-1].set_xlabel("Time (s)")
        fig.tight_layout()
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return str(out)


_DIGEST_PARAM_KEYS = ("freq", "psu_ch1_V", "psu_ch3_V", "smu1_V", "smu2_V")
_DIGEST_STAT_KEYS = (
    "avg_X",
    "avg_Y",
    "avg_R",
    "avg_theta",
    "rmse_X",
    "rmse_Y",
    "rmse_R",
    "xcorr_XY",
    "drift_R_slope",
    "drift_R_intercept",
)


def _load_digest(csv_path: Path) -> dict:
    """Load a digest dict from an already-compiled ``*_digest.csv`` (fast path,
    matching the columns written by ``LIASnapDigest.compile()``) or, failing
    that, a raw snap CSV (recomputed via ``LIASnapDigest``).
    """
    with open(csv_path, newline="") as f:
        header = next(csv.reader(f), [])
    if header and header[0].strip() == "freq":
        with open(csv_path, newline="") as f:
            row = next(csv.DictReader(f))
        params = {
            k: float(row[k])
            for k in _DIGEST_PARAM_KEYS
            if row.get(k, "") not in ("", None)
        }
        digest: dict = {k: float(row[k]) for k in _DIGEST_STAT_KEYS}
        digest["params"] = params
        return digest
    return LIASnapDigest(str(csv_path)).digest()


class LIAFrequencyResponseCompiler:
    """Summarize digest CSVs across a frequency sweep into R, theta, and R-drift plots.

    Accepts either already-compiled ``*_digest.csv`` files or raw snap CSVs
    (via ``_load_digest``). Produces three separate figures rather than one
    combined subplot grid, since each is read independently: R (with error
    bars from ``rmse_R`` conveying measurement noise), theta (optionally
    shifted by a constant phase offset), and the linear R-drift rate.
    """

    def __init__(
        self,
        csv_paths: list[str],
        out_name: str | None = None,
        phase_shift_deg: float = 0.0,
    ):
        if len(csv_paths) < 2:
            raise ValueError("need at least 2 CSVs to plot a frequency response")
        self.csv_paths = [Path(p).resolve() for p in csv_paths]
        self.out_name = out_name
        self.phase_shift_deg = phase_shift_deg

    def compile(self) -> list[str]:
        digests = [_load_digest(p) for p in self.csv_paths]

        missing = [
            p.name for p, d in zip(self.csv_paths, digests) if "freq" not in d["params"]
        ]
        if missing:
            raise ValueError(f"'freq' missing in: {missing}")

        order = np.argsort([d["params"]["freq"] for d in digests])
        digests = [digests[i] for i in order]
        freqs = [d["params"]["freq"] for d in digests]

        for freq, d in zip(freqs, digests):
            logger.info(
                "freq = %g Hz: avg_R = %.6g, rmse_R = %.6g, drift_R_slope = %.6g",
                freq,
                d["avg_R"],
                d["rmse_R"],
                d["drift_R_slope"],
            )

        stem = self.out_name or "freq_response"
        anchor = self.csv_paths[0]
        out_dir = _output_path(anchor, "").parent
        out_dir.mkdir(parents=True, exist_ok=True)

        return [
            self._plot_r(freqs, digests, out_dir / f"{stem}_R.png"),
            self._plot_theta(freqs, digests, out_dir / f"{stem}_theta.png"),
            self._plot_drift(freqs, digests, out_dir / f"{stem}_drift.png"),
        ]

    def _new_axes(self, ylabel: str, title: str):
        fig, ax = plt.subplots(figsize=(8, 5))
        fig.suptitle(title)
        ax.set_xscale("log")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel(ylabel)
        ax.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.7)
        fmt = ticker.FuncFormatter(PlotCompiler._smart_fmt)
        ax.xaxis.set_major_formatter(fmt)
        ax.yaxis.set_major_formatter(fmt)
        return fig, ax

    def _save(self, fig, out: Path) -> str:
        fig.tight_layout()
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return str(out)

    def _plot_r(self, freqs: list[float], digests: list[dict], out: Path) -> str:
        title = f"R vs frequency ({len(digests)} points)"
        fig, ax = self._new_axes("Average R (V)", title)
        avg_r = [d["avg_R"] for d in digests]
        rmse_r = [d["rmse_R"] for d in digests]
        ax.errorbar(
            freqs,
            avg_r,
            yerr=rmse_r,
            fmt="o-",
            markersize=4,
            linewidth=1,
            capsize=3,
            ecolor="0.4",
            elinewidth=0.8,
        )
        return self._save(fig, out)

    def _plot_theta(self, freqs: list[float], digests: list[dict], out: Path) -> str:
        title = f"Theta vs frequency ({len(digests)} points)"
        if self.phase_shift_deg:
            title += f", shifted by {self.phase_shift_deg:+g} deg"
        fig, ax = self._new_axes("Theta (deg)", title)
        theta = [
            ((d["avg_theta"] + self.phase_shift_deg + 180) % 360) - 180 for d in digests
        ]
        ax.plot(freqs, theta, marker="o", markersize=4, linewidth=1)
        return self._save(fig, out)

    def _plot_drift(self, freqs: list[float], digests: list[dict], out: Path) -> str:
        title = f"R drift vs frequency ({len(digests)} points)"
        fig, ax = self._new_axes("R drift (V/s)", title)
        drift = [d["drift_R_slope"] for d in digests]
        ax.axhline(0, color="0.6", linewidth=0.8, linestyle="--")
        ax.plot(freqs, drift, marker="o", markersize=4, linewidth=1, color="C1")
        return self._save(fig, out)


def _exp_model(t: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    return a * np.exp(b * t) + c


class LIADriftEvolutionCompiler:
    """Analyze how a sweep folder's per-file R-drift rate evolves over the
    course of capture.

    Each CSV in ``csv_paths`` is one frequency point's digest (or raw snap,
    via ``_load_digest``); they were captured sequentially, lowest frequency
    first, ``interval_s`` apart. Treating each file's ``drift_R_slope`` as one
    sample of a coarser time series, this fits an exponential trend to the
    drift-over-time curve (first derivative of R, i.e. "the drift") and
    computes its rate of change (second derivative of R, i.e. "the change of
    the change of R").
    """

    def __init__(
        self, csv_paths: list[str], interval_s: float, out_name: str | None = None
    ):
        if len(csv_paths) < 3:
            raise ValueError("need at least 3 CSVs to fit a drift evolution")
        self.csv_paths = [Path(p).resolve() for p in csv_paths]
        self.interval_s = interval_s
        self.out_name = out_name

    def compile(self) -> str:
        digests = [_load_digest(p) for p in self.csv_paths]

        missing = [
            p.name for p, d in zip(self.csv_paths, digests) if "freq" not in d["params"]
        ]
        if missing:
            raise ValueError(f"'freq' missing in: {missing}")

        order = np.argsort([d["params"]["freq"] for d in digests])
        digests = [digests[i] for i in order]

        n = len(digests)
        t = np.arange(n) * self.interval_s
        drift = np.array([d["drift_R_slope"] for d in digests])
        rate = np.gradient(drift, t)
        accel = np.gradient(rate, t)

        for i in range(n):
            logger.info(
                "t=%.0fs: drift_R=%.6g V/s, d(drift)/dt=%.6g V/s^2, "
                "d^2(drift)/dt^2=%.6g V/s^3",
                t[i],
                drift[i],
                rate[i],
                accel[i],
            )

        p0 = (drift[0] - drift[-1], 0.0, drift[-1])
        try:
            (a, b, c), _ = curve_fit(_exp_model, t, drift, p0=p0, maxfev=10000)
        except RuntimeError:
            logger.warning("exponential fit did not converge; falling back to p0")
            a, b, c = p0

        stem = self.out_name or "drift_evolution"
        anchor = self.csv_paths[0]
        out = _output_path(anchor, "").parent / f"{stem}.png"
        out.parent.mkdir(parents=True, exist_ok=True)

        fmt = ticker.FuncFormatter(PlotCompiler._smart_fmt)
        fig, (ax_drift, ax_accel) = plt.subplots(2, 1, sharex=True, figsize=(8, 8))
        fig.suptitle(f"R-drift evolution across sweep ({n} points)")

        ax_drift.plot(
            t,
            drift,
            marker="o",
            markersize=4,
            linewidth=1,
            color="C1",
            label="drift_R_slope",
        )
        t_fit = np.linspace(t[0], t[-1], 200)
        ax_drift.plot(
            t_fit,
            _exp_model(t_fit, a, b, c),
            color="red",
            linewidth=1.2,
            linestyle="--",
            label="exponential fit",
        )
        ax_drift.set_ylabel("R drift (V/s)")
        ax_drift.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
        ax_drift.yaxis.set_major_formatter(fmt)
        ax_drift.legend(loc="upper right", fontsize=8)

        txt = (
            f"drift(t) = {a:+.3e}·exp({b:+.3e}·t) {c:+.3e}\n"
            f"A={a:+.3e}, B={b:+.3e}, C={c:+.3e}"
        )
        ax_drift.text(
            0.02,
            0.05,
            txt,
            transform=ax_drift.transAxes,
            va="bottom",
            ha="left",
            fontsize=8,
            family="monospace",
            color="darkred",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
        )

        ax_accel.axhline(0, color="0.6", linewidth=0.8, linestyle="--")
        ax_accel.plot(t, accel, marker="o", markersize=4, linewidth=1, color="C2")
        ax_accel.set_ylabel("d²(drift)/dt² (V/s³)")
        ax_accel.set_xlabel("Time (s)")
        ax_accel.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
        ax_accel.yaxis.set_major_formatter(fmt)

        fig.tight_layout()
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return str(out)


# (color, linestyle) per marker slot, in the order markers are drawn. Cycled
# (via modulo) by plot_channels_timeseries_marks once more marks are pressed
# than there are distinct slots.
_EVENT_MARKER_STYLES = (
    ("black", ":"),
    ("darkorange", "-."),
    ("purple", "--"),
    ("teal", "-."),
    ("crimson", ":"),
)


def plot_channels_timeseries_marks(
    csv_path: str,
    t: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    r: np.ndarray,
    marks: list[tuple[int, str]],
    out_suffix: str = "_timeseries.png",
    labels: tuple[str, str, str] = ("X (V)", "Y (V)", "R (V)"),
) -> str:
    """Plot three channels vs time with an arbitrary number of operator-marked events.

    Used by capture modes (e.g. ``gas_response_interactive``, X/Y/R by
    default) where the operator can mark any number of points. ``marks`` is a
    list of ``(index, label)`` pairs, in the order they were pressed;
    out-of-range indices are silently skipped. Marker color/linestyle cycles
    through ``_EVENT_MARKER_STYLES`` once it runs out of distinct slots.
    ``labels`` names the three traces (e.g. ``("X (V)", "Y (V)", "Theta (deg)")``
    for a phase-calibration run) — the trace values themselves are always
    ``x``, ``y``, ``r`` positionally.
    """
    out = _output_path(Path(csv_path).resolve(), out_suffix)
    out.parent.mkdir(parents=True, exist_ok=True)

    traces = [(x, labels[0], "C0"), (y, labels[1], "C1"), (r, labels[2], "C2")]
    fig, axes = plt.subplots(len(traces), 1, sharex=True, figsize=(8, 8))
    fig.suptitle(Path(csv_path).stem)

    events = [
        (idx, label) for idx, label in marks if idx is not None and 0 <= idx < len(t)
    ]

    fmt = ticker.FuncFormatter(PlotCompiler._smart_fmt)
    for ax, (data, label, color) in zip(axes, traces):
        ax.plot(t, data, linewidth=0.8, color=color)
        ax.set_ylabel(label)
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
        ax.yaxis.set_major_formatter(fmt)
        for i, (idx, event_lbl) in enumerate(events):
            marker_color, marker_style = _EVENT_MARKER_STYLES[
                i % len(_EVENT_MARKER_STYLES)
            ]
            ax.axvline(
                t[idx],
                color=marker_color,
                linewidth=1.2,
                linestyle=marker_style,
                label=event_lbl or "event",
            )
        if events:
            ax.legend(loc="upper right", fontsize=7)

    axes[-1].set_xlabel("Time (s)")
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)


def plot_r_monitor_session(
    csv_path: str,
    t: list[float],
    r: list[float],
    theta: list[float],
    events: list[tuple[int, str]],
    drift_window_s: float = 60.0,
    out_suffix: str = "_timeseries.png",
) -> str:
    """Plot R and theta vs time for a continuous operating-point monitoring
    session as plain lines (no legends, markers or fit overlays), followed by
    a text summary of the changes/attempts narrated via ``note_event`` (one
    line per event with its time) and the whole-run / last-window drift
    slopes of R.
    """
    import textwrap

    t_arr = np.asarray(t, dtype=float)
    r_arr = np.asarray(r, dtype=float)
    theta_arr = np.asarray(theta, dtype=float)

    out = _output_path(Path(csv_path).resolve(), out_suffix)
    out.parent.mkdir(parents=True, exist_ok=True)

    valid_events = [
        (idx, label)
        for idx, label in events
        if idx is not None and 0 <= idx < len(t_arr)
    ]
    lines = []
    for idx, label in valid_events:
        text = f"{t_arr[idx]:7.0f}s  {(label or 'event').strip(chr(34))}"
        lines.extend(textwrap.wrap(text, width=95, subsequent_indent=" " * 10))

    drift_txt = ""
    if len(t_arr) >= 2:
        slope, _ = _linear_drift_fit(t_arr, r_arr)
        drift_txt = (
            f"R whole-run drift {slope:+.3e} V/s ({slope * 3600:+.3e} V/hr), "
            f"dR over run {slope * (t_arr[-1] - t_arr[0]):+.3e} V"
        )
        window_mask = t_arr >= (t_arr[-1] - drift_window_s)
        if window_mask.sum() >= 2:
            w_slope, _ = _linear_drift_fit(t_arr[window_mask], r_arr[window_mask])
            drift_txt += f"; last {drift_window_s:g}s {w_slope:+.3e} V/s"

    summary_height = 0.5 + 0.17 * (len(lines) + 2)
    fig = plt.figure(figsize=(9, 6.5 + summary_height))
    grid = fig.add_gridspec(
        3, 1, height_ratios=[3, 3, summary_height], hspace=0.25,
        top=0.96, bottom=0.01,
    )
    ax_r = fig.add_subplot(grid[0])
    ax_theta = fig.add_subplot(grid[1], sharex=ax_r)
    ax_txt = fig.add_subplot(grid[2])
    fig.suptitle(Path(csv_path).stem, y=0.985)

    fmt = ticker.FuncFormatter(PlotCompiler._smart_fmt)
    for ax, data, label in (
        (ax_r, r_arr, "R (V)"),
        (ax_theta, theta_arr, "theta (deg)"),
    ):
        ax.plot(t_arr, data, linewidth=0.8, color="C0")
        ax.set_ylabel(label)
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
        ax.yaxis.set_major_formatter(fmt)
    ax_theta.set_xlabel("Time (s)")

    ax_txt.axis("off")
    header = "Summary of changes and attempts"
    body = "\n".join(lines) if lines else "(no events recorded)"
    ax_txt.text(
        0.0, 1.0, f"{header}\n{drift_txt}\n\n{body}",
        transform=ax_txt.transAxes, va="top", ha="left",
        fontsize=7, family="monospace",
    )

    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)


class OperatingPointOffsetCompiler:
    """Plot SCU1/SCU2 current vs LIA offset from an in-memory sweep of
    ``{heater_voltage, lia_offset, channel, measured_current}`` rows, as
    produced by ``OperatingPointOffsetSweep``.

    Unlike the other compilers in this module, the rows are taken directly
    from the caller rather than re-derived from CSVs on disk, mirroring
    ``OperatingPointIVCompiler``.
    """

    def __init__(self, rows: list[dict], anchor_csv: str):
        if not rows:
            raise ValueError(
                "need at least 1 row to plot an operating-point offset sweep"
            )
        self.rows = rows
        self.anchor_csv = Path(anchor_csv).resolve()

    def _out_dir(self) -> Path:
        out_dir = _output_path(self.anchor_csv, "").parent
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def compile(self) -> list[str]:
        """One plot per channel, overlaying every heater_voltage, of measured
        current vs LIA offset."""
        channels = sorted({row["channel"] for row in self.rows})
        heater_voltages = sorted({row["heater_voltage"] for row in self.rows})
        out_paths = []
        for channel in channels:
            fig, ax = plt.subplots(figsize=(7, 5))
            fmt = ticker.FuncFormatter(PlotCompiler._smart_fmt)
            for heater_voltage in heater_voltages:
                matched = sorted(
                    (row["lia_offset"], row["measured_current"])
                    for row in self.rows
                    if row["channel"] == channel
                    and row["heater_voltage"] == heater_voltage
                )
                xs = [m[0] for m in matched]
                ys = [m[1] for m in matched]
                ax.plot(
                    xs,
                    ys,
                    marker="o",
                    markersize=4,
                    linewidth=1,
                    label=f"{heater_voltage:g}V heater",
                )
            ax.set_xlabel("LIA offset (V)")
            ax.set_ylabel("SCU current (A)")
            ax.set_title(f"{channel} current vs offset")
            ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
            ax.yaxis.set_major_formatter(fmt)
            ax.legend(loc="best", fontsize=7)

            fig.tight_layout()
            out = self._out_dir() / f"{channel}_current_vs_offset.png"
            fig.savefig(out, dpi=150, bbox_inches="tight")
            plt.close(fig)
            out_paths.append(str(out))
        return out_paths


class OperatingPointIVCompiler:
    """Plot SCU1/SCU2 IV curves from an in-memory sweep of ``{heater_voltage,
    lia_offset, channel, set_voltage, measured_current}`` rows, as produced by
    ``OperatingPointSweep``.

    Unlike the other compilers in this module, the rows are taken directly
    from the caller rather than re-derived from CSVs on disk.
    """

    def __init__(self, rows: list[dict], anchor_csv: str):
        if not rows:
            raise ValueError("need at least 1 row to plot an operating-point IV sweep")
        self.rows = rows
        self.anchor_csv = Path(anchor_csv).resolve()

    def _out_dir(self) -> Path:
        out_dir = _output_path(self.anchor_csv, "").parent
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def compile_offset_overlays(self) -> list[str]:
        """One IV plot per (heater_voltage, channel), overlaying every lia_offset."""
        heater_voltages = sorted({row["heater_voltage"] for row in self.rows})
        channels = sorted({row["channel"] for row in self.rows})
        out_paths = []
        for heater_voltage in heater_voltages:
            for channel in channels:
                subset = [
                    row
                    for row in self.rows
                    if row["heater_voltage"] == heater_voltage
                    and row["channel"] == channel
                ]
                out_name = f"{heater_voltage:g}V_{channel}_iv_vs_offset.png"
                out_paths.append(
                    self._plot_iv(
                        subset,
                        series_key="lia_offset",
                        series_label="V offset",
                        title=f"{channel} IV @ heater {heater_voltage:g}V",
                        out_name=out_name,
                    )
                )
        return out_paths

    def compile_heater_overlay(self, offset_value: float) -> list[str]:
        """One IV plot per channel at a fixed offset, overlaying every
        heater_voltage."""
        matched_offset = self._nearest_offset(offset_value)
        channels = sorted({row["channel"] for row in self.rows})
        out_paths = []
        for channel in channels:
            subset = [
                row
                for row in self.rows
                if row["channel"] == channel and row["lia_offset"] == matched_offset
            ]
            out_name = f"offset_{matched_offset:g}V_{channel}_iv_vs_heater.png"
            out_paths.append(
                self._plot_iv(
                    subset,
                    series_key="heater_voltage",
                    series_label="V heater",
                    title=f"{channel} IV @ offset {matched_offset:g}V",
                    out_name=out_name,
                )
            )
        return out_paths

    def _nearest_offset(self, offset_value: float) -> float:
        offsets = sorted({row["lia_offset"] for row in self.rows})
        nearest = min(offsets, key=lambda v: abs(v - offset_value))
        if abs(nearest - offset_value) > 1e-9:
            logger.warning(
                f"plot_offset_value={offset_value:g} not found in "
                f"swept offsets {offsets}; using nearest match {nearest:g}"
            )
        return nearest

    def _plot_iv(
        self,
        rows: list[dict],
        series_key: str,
        series_label: str,
        title: str,
        out_name: str,
    ) -> str:
        series_values = sorted({row[series_key] for row in rows})

        fig, ax = plt.subplots(figsize=(7, 5))
        fmt = ticker.FuncFormatter(PlotCompiler._smart_fmt)
        for series_val in series_values:
            matched = sorted(
                (row["set_voltage"], row["measured_current"])
                for row in rows
                if row[series_key] == series_val
            )
            xs = [m[0] for m in matched]
            ys = [m[1] for m in matched]
            ax.plot(
                xs,
                ys,
                marker="o",
                markersize=4,
                linewidth=1,
                label=f"{series_val:g} {series_label}",
            )
        ax.set_xlabel("SCU voltage (V)")
        ax.set_ylabel("SCU current (A)")
        ax.set_xscale("log")
        ax.set_title(title)
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
        ax.yaxis.set_major_formatter(fmt)
        ax.legend(loc="best", fontsize=7)

        fig.tight_layout()
        out = self._out_dir() / out_name
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return str(out)


def fit_iv(v: np.ndarray, i: np.ndarray) -> dict:
    """Linear fit ``I = slope * V + intercept``; returns slope, intercept,
    resistance (1/slope), R^2 and MSE (mean squared residual, A^2)."""
    slope, intercept = np.polyfit(v, i, 1)
    resid = i - (slope * v + intercept)
    ss_tot = float(np.sum((i - np.mean(i)) ** 2))
    r2 = 1.0 - float(np.sum(resid**2)) / ss_tot if ss_tot else float("nan")
    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "resistance": 1.0 / float(slope) if slope else float("inf"),
        "r2": r2,
        "mse": float(np.mean(resid**2)),
    }


def heater_resistance_fits(rows: list[dict]) -> dict[int, dict]:
    """Per-channel pooled fit over every repeat's points."""
    fits = {}
    for ch in sorted({r["channel"] for r in rows}):
        pts = [r for r in rows if r["channel"] == ch]
        fits[ch] = fit_iv(
            np.array([r["mean_voltage"] for r in pts]),
            np.array([r["mean_current"] for r in pts]),
        )
    return fits


class HeaterResistanceCompiler:
    """Plot I-V points, linear fit, R^2 and MSE-based error lines for each
    heater channel in a ``heater_resistance.csv`` written by
    ``HeaterResistanceSetup``."""

    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path).resolve()
        with open(self.csv_path, newline="") as f:
            self.rows = [
                {
                    "repeat": int(r["repeat"]),
                    "channel": int(r["channel"]),
                    "set_voltage": float(r["set_voltage"]),
                    "mean_voltage": float(r["mean_voltage"]),
                    "mean_current": float(r["mean_current"]),
                    "sem_current": float(r["sem_current"]),
                }
                for r in csv.DictReader(f)
            ]
        if not self.rows:
            raise ValueError(f"no rows in {csv_path}")

    def compile(self) -> list[str]:
        fits = heater_resistance_fits(self.rows)
        out_paths = []
        for ch, fit in fits.items():
            pts = [r for r in self.rows if r["channel"] == ch]
            setv = sorted({r["set_voltage"] for r in pts})
            xs, ys, errs = [], [], []
            for sv in setv:
                grp = [r for r in pts if r["set_voltage"] == sv]
                cur = np.array([r["mean_current"] for r in grp])
                xs.append(float(np.mean([r["mean_voltage"] for r in grp])))
                ys.append(float(cur.mean()))
                errs.append(
                    float(cur.std(ddof=1))
                    if len(cur) > 1
                    else float(grp[0]["sem_current"])
                )
            xs, ys, errs = map(np.array, (xs, ys, errs))
            rmse = np.sqrt(fit["mse"])
            xf = np.linspace(xs.min(), xs.max(), 100)
            yf = fit["slope"] * xf + fit["intercept"]

            fig, ax = plt.subplots(figsize=(8, 5.5))
            ax.errorbar(
                xs, ys * 1e3, yerr=errs * 1e3, fmt="o", capsize=3,
                label="mean over repeats (± std)",
            )
            ax.plot(xf, yf * 1e3, "-", label="linear fit")
            ax.fill_between(
                xf, (yf - rmse) * 1e3, (yf + rmse) * 1e3, alpha=0.2,
                label=f"fit ± RMSE ({rmse * 1e3:.3f} mA)",
            )
            ax.set_xlabel("Heater voltage (V)")
            ax.set_ylabel("Heater current (mA)")
            ax.set_title(f"PSU ch{ch} heater I-V")
            ax.grid(True, alpha=0.3)
            ax.legend(loc="upper left")
            ax.text(
                0.98, 0.05,
                f"R = {fit['resistance']:.1f} Ω\nR² = {fit['r2']:.4f}\n"
                f"MSE = {fit['mse']:.3e} A²",
                transform=ax.transAxes, ha="right", va="bottom",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
            )
            out = _output_path(self.csv_path, f"_ch{ch}.png")
            out.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(out, dpi=150, bbox_inches="tight")
            plt.close(fig)
            out_paths.append(str(out))
        return out_paths
