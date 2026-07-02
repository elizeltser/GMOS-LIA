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
    """Digest a single SR860 snap CSV: avg X/Y/R and RMSE of X/Y."""

    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path).resolve()
        self.params: dict[str, float] = {}
        self._t: np.ndarray | None = None
        self._x: np.ndarray | None = None
        self._y: np.ndarray | None = None
        self._r: np.ndarray | None = None
        self._parse()

    def _parse(self) -> None:
        params: dict[str, float] = {}
        data_rows: list[list[str]] = []
        in_data = False
        with open(self.csv_path, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                if not in_data:
                    if row[0].strip().lower() == "time":
                        in_data = True
                        continue
                    key = row[0].strip()
                    if key in _PARAM_KEYS and len(row) > 1 and row[1].strip():
                        try:
                            params[key] = float(row[1])
                        except ValueError:
                            pass
                    continue
                if len(row) >= 4:
                    data_rows.append(row)
        if not in_data:
            raise ValueError(f"{self.csv_path}: no 'time,X,Y,R' header found")

        arr = np.array([[float(c) for c in r[:4]] for r in data_rows])
        self.params = params
        self._t = arr[:, 0]
        self._x = arr[:, 1]
        self._y = arr[:, 2]
        self._r = arr[:, 3]

    def digest(self) -> dict:
        assert self._x is not None and self._y is not None and self._r is not None
        rmse_x = float(np.std(self._x))
        rmse_y = float(np.std(self._y))
        return {
            "avg_X": float(np.mean(self._x)),
            "avg_Y": float(np.mean(self._y)),
            "avg_R": float(np.mean(self._r)),
            "rmse_X": rmse_x,
            "rmse_Y": rmse_y,
            "rmse_R": float(np.hypot(rmse_x, rmse_y)),
            "xcorr_XY": self._xcorr(),
            "params": dict(self.params),
        }

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
        keys = list(_PARAM_KEYS)
        stat_keys = [
            "avg_X", "avg_Y", "avg_R", "rmse_X", "rmse_Y", "rmse_R", "xcorr_XY",
        ]
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(keys + stat_keys)
            row = [d["params"].get(k, "") for k in keys] + [d[k] for k in stat_keys]
            w.writerow(row)

        print(f"Digest for {self.csv_path.name}:")
        for k in keys:
            if k in d["params"]:
                print(f"  {k:10s} = {d['params'][k]}")
        for k in stat_keys:
            print(f"  {k:10s} = {d[k]:.6g}")
        return str(out)

    def plot_timeseries(self) -> str:
        """Plot X, Y and R as a function of time into a single PNG."""
        assert (
            self._t is not None and self._x is not None
            and self._y is not None and self._r is not None
        )
        out = _output_path(self.csv_path, "_timeseries.png")
        out.parent.mkdir(parents=True, exist_ok=True)

        traces = [
            (self._x, "X (V)"),
            (self._y, "Y (V)"),
            (self._r, "R (V)"),
        ]
        fig, axes = plt.subplots(len(traces), 1, sharex=True, figsize=(8, 9))
        fig.suptitle(self.csv_path.stem)

        fmt = ticker.FuncFormatter(PlotCompiler._smart_fmt)
        for ax, (data, label) in zip(axes, traces):
            ax.plot(self._t, data, linewidth=0.8)
            ax.set_ylabel(label)
            ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
            ax.yaxis.set_major_formatter(fmt)

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
