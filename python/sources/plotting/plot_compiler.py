import csv
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


class PlotCompiler:
    def __init__(self, csv_path: str, x_scale: str = "linear", y_scale: str = "linear"):
        self.csv_path = Path(csv_path).resolve()
        self.x_scale = x_scale
        self.y_scale = y_scale

    def compile(self) -> str:
        x_data, y_data, x_label, y_label, title = self._read_csv()

        fig, ax = plt.subplots()
        ax.plot(x_data, y_data, marker="o", markersize=3, linewidth=1)

        ax.set_xscale(self.x_scale)
        ax.set_yscale(self.y_scale)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_title(title)

        fmt = ticker.FuncFormatter(self._smart_fmt)
        ax.xaxis.set_major_formatter(fmt)
        ax.yaxis.set_major_formatter(fmt)

        ax.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.7)

        out = self._output_path()
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return str(out)

    def _read_csv(self) -> tuple:
        with open(self.csv_path, newline="") as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

        x_label = headers[1].strip()
        y_label = headers[2].strip()
        x_data = [float(row[1]) for row in rows if len(row) > 2]
        y_data = [float(row[2]) for row in rows if len(row) > 2]
        title = self.csv_path.stem
        return x_data, y_data, x_label, y_label, title

    def _output_path(self) -> Path:
        # Map Results/…/foo.csv → Plots/…/foo.png relative to project root
        parts = self.csv_path.parts
        try:
            results_idx = next(i for i, p in enumerate(parts) if p == "Results")
            rel = Path(*parts[results_idx + 1:])
        except StopIteration:
            rel = Path(self.csv_path.name)

        project_root = self.csv_path
        for _ in range(len(parts) - (parts.index("Results") if "Results" in parts else 0)):
            project_root = project_root.parent
            if (project_root / "Results").exists():
                break

        return project_root / "Plots" / rel.with_suffix(".png")

    @staticmethod
    def _smart_fmt(x: float, _pos) -> str:
        if x == 0:
            return "0"
        return f"{float(f'{x:.3g}'):g}"


class LIAPlotCompiler:
    """Plot X and R channels from a LIA measurement CSV (columns: time, X, R)."""

    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path).resolve()

    def compile(self) -> str:
        time_data, x_data, r_data, theta_data = self._read_csv()

        fig, (ax_x, ax_y, ax_theta) = plt.subplots(3, 1, sharex=True, figsize=(8, 5))
        fig.suptitle(self.csv_path.stem)

        ax_x.plot(time_data, x_data, linewidth=1)
        ax_x.set_ylabel("X (V)")
        ax_x.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)

        ax_y.plot(time_data, r_data, linewidth=1, color="C1")
        ax_y.set_ylabel("Y (V)")
        ax_y.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)

        ax_theta.plot(time_data, theta_data, linewidth=1)
        ax_theta.set_ylabel("Theta (R)")
        ax_theta.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
        ax_theta.set_xlabel("Time (s)")
        
        fmt = ticker.FuncFormatter(PlotCompiler._smart_fmt)
        for ax in (ax_x, ax_y):
            ax.yaxis.set_major_formatter(fmt)
        ax_y.xaxis.set_major_formatter(fmt)

        fig.tight_layout()

        out = self._output_path()
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return str(out)

    def _read_csv(self) -> tuple:
        with open(self.csv_path, newline="") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)
        time_data  = [float(row[0]) for row in rows if len(row) >= 3]
        x_data     = [float(row[1]) for row in rows if len(row) >= 3]
        y_data     = [float(row[2]) for row in rows if len(row) >= 3]
        theta_data = [float(row[3]) for row in rows if len(row) >= 3]

        return time_data, x_data, y_data, theta_data

    def _output_path(self) -> Path:
        parts = self.csv_path.parts
        try:
            results_idx = next(i for i, p in enumerate(parts) if p == "Results")
            rel = Path(*parts[results_idx + 1:])
        except StopIteration:
            rel = Path(self.csv_path.name)

        project_root = self.csv_path
        for _ in range(len(parts) - (parts.index("Results") if "Results" in parts else 0)):
            project_root = project_root.parent
            if (project_root / "Results").exists():
                break

        return project_root / "Plots" / rel.with_suffix(".png")


class LIAPhaseZeroPlotCompiler:
    """Plot SCU1/SCU2 currents and LIA phase vs time from a phase_zero CSV
    (columns: time, v_scu1, v_scu2, i_scu1, i_scu2, theta)."""

    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path).resolve()

    def compile(self) -> str:
        time_data, i1_data, i2_data, theta_data = self._read_csv()

        fig, (ax_i1, ax_i2, ax_theta) = plt.subplots(3, 1, sharex=True, figsize=(8, 6))
        fig.suptitle(self.csv_path.stem)

        ax_i1.plot(time_data, i1_data, linewidth=1)
        ax_i1.set_ylabel("I SCU1 (A)")
        ax_i1.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)

        ax_i2.plot(time_data, i2_data, linewidth=1, color="C1")
        ax_i2.set_ylabel("I SCU2 (A)")
        ax_i2.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)

        ax_theta.plot(time_data, theta_data, linewidth=1, color="C2")
        ax_theta.set_ylabel("Theta (deg)")
        ax_theta.set_xlabel("Time (s)")
        ax_theta.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)

        fmt = ticker.FuncFormatter(PlotCompiler._smart_fmt)
        for ax in (ax_i1, ax_i2, ax_theta):
            ax.yaxis.set_major_formatter(fmt)
        ax_theta.xaxis.set_major_formatter(fmt)

        fig.tight_layout()

        out = self._output_path()
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return str(out)

    def _read_csv(self) -> tuple:
        with open(self.csv_path, newline="") as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)
        time_data  = [float(row[0]) for row in rows if len(row) >= 6]
        i1_data    = [float(row[3]) for row in rows if len(row) >= 6]
        i2_data    = [float(row[4]) for row in rows if len(row) >= 6]
        theta_data = [float(row[5]) for row in rows if len(row) >= 6]
        return time_data, i1_data, i2_data, theta_data

    def _output_path(self) -> Path:
        parts = self.csv_path.parts
        try:
            results_idx = next(i for i, p in enumerate(parts) if p == "Results")
            rel = Path(*parts[results_idx + 1:])
        except StopIteration:
            rel = Path(self.csv_path.name)

        project_root = self.csv_path
        for _ in range(len(parts) - (parts.index("Results") if "Results" in parts else 0)):
            project_root = project_root.parent
            if (project_root / "Results").exists():
                break

        return project_root / "Plots" / rel.with_suffix(".png")
