import argparse
import logging
import os
import sys

# Add python/sources/ to path so ATE and setups are importable as top-level packages
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import setups
from gmos_repl import run_repl
from plotting import (
    LIADiffSweepScatterCompiler,
    LIAPlotCompiler,
    LIASnapDigest,
    LIASweepScatterCompiler,
    NoiseEvalCompiler,
    PlotCompiler,
)
from setups import SetupBase
from visa_enumeration import list_devices

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="GMOS LIA Experiment Runner")
    parser.add_argument("--experiment", "-e", help="Experiment name")
    parser.add_argument("--config", "-c", help="Config file path")
    parser.add_argument("--list_devices", action="store_true",
                        help="List all available VISA resources and exit")
    parser.add_argument("--repl", action="store_true",
                        help="Enter interactive REPL")
    parser.add_argument("--log", action="store_true",
                        help="With --repl: also log to <repo_root>/repl.log")
    parser.add_argument("--scu", default="SCU1",
                        help="SCU device tag to be used for IV sweep (default: SCU1)")
    parser.add_argument("--output-name", metavar="NAME",
                        help="Custom result filename stem (no extension); omit for auto date-stamped name")
    parser.add_argument("--compile-2d-plot", metavar="CSV",
                        help="Path to a result .csv file to compile into a 2D plot")
    parser.add_argument("--compile-lia-plot", metavar="CSV",
                        help="Path to a LIA result .csv file to compile X and R plots")
    parser.add_argument("--compile-noise-plot", metavar="CSV",
                        help="Path to noise evaluation summary file")
    parser.add_argument("--lia-digest", metavar="CSV",
                        help="Digest a single LIA snap CSV (avg X/Y/R, X/Y RMSE)")
    parser.add_argument("--lia-sweep-scatter", nargs="+", metavar="CSV",
                        help="LIA snap CSVs to scatter against a swept parameter")
    parser.add_argument("--lia-diff-baseline", nargs="+", metavar="CSV",
                        help="Baseline (e.g. nogas) LIA snap CSVs for a difference sweep")
    parser.add_argument("--lia-diff-signal", nargs="+", metavar="CSV",
                        help="Signal (e.g. gas) LIA snap CSVs; subtracted against --lia-diff-baseline")
    parser.add_argument("--sweep-param", choices=["freq", "offset", "sr560_amp"],
                        help="Parameter swept across --lia-sweep-scatter inputs")
    parser.add_argument("--x-scale", choices=["linear", "log"], default="linear",
                        help="X-axis scale (default: linear)")
    parser.add_argument("--y-scale", choices=["linear", "log"], default="linear",
                        help="Y-axis scale (default: linear)")
    parser.add_argument("--duration", type=float, default=60.0,
                        help="lia_snap_only: total measurement duration in seconds (default: 60)")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="lia_snap_only: sample interval in seconds (default: 1)")
    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return

    if args.repl:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        log_path = os.path.join(repo_root, "repl.log") if args.log else None
        run_repl(log_path=log_path)
        return

    if args.compile_2d_plot:
        compiler = PlotCompiler(args.compile_2d_plot, x_scale=args.x_scale, y_scale=args.y_scale)
        out_path = compiler.compile()
        print(f"Plot saved to: {out_path}")
        return

    if args.compile_lia_plot:
        compiler = LIAPlotCompiler(args.compile_lia_plot)
        out_path = compiler.compile()
        print(f"Plot saved to: {out_path}")
        return

    if args.compile_noise_plot:
        compiler = NoiseEvalCompiler(args.compile_noise_plot)
        out_path = compiler.compile()
        print(f"Plot saved to: {out_path}")
        return

    if args.lia_digest:
        digest = LIASnapDigest(args.lia_digest)
        out_path = digest.compile()
        print(f"Digest saved to: {out_path}")
        plot_path = digest.plot_timeseries()
        print(f"Time-series plot saved to: {plot_path}")
        return

    if args.lia_sweep_scatter:
        if not args.sweep_param:
            parser.error("--sweep-param is required with --lia-sweep-scatter")
        out_path = LIASweepScatterCompiler(
            args.lia_sweep_scatter, args.sweep_param, out_name=args.output_name,
        ).compile()
        print(f"Plot saved to: {out_path}")
        return

    if args.lia_diff_signal or args.lia_diff_baseline:
        if not (args.lia_diff_signal and args.lia_diff_baseline):
            parser.error("--lia-diff-baseline and --lia-diff-signal must be given together")
        if not args.sweep_param:
            parser.error("--sweep-param is required with --lia-diff-signal/--lia-diff-baseline")
        out_path = LIADiffSweepScatterCompiler(
            args.lia_diff_baseline, args.lia_diff_signal, args.sweep_param,
            out_name=args.output_name,
        ).compile()
        print(f"Plot saved to: {out_path}")
        return

    if not args.experiment:
        parser.error("--experiment / -e is required unless --list_devices, --repl, or --compile-2d-plot is used")

    logger.info(f"Starting experiment: {args.experiment}")

    experiment: SetupBase | None = None
    if args.experiment == "IV-voltage-lin":
        experiment = setups.IVSweep(scale="linear", scu_tag=args.scu, mode="voltage", output_name=args.output_name)
        experiment.run()
    elif args.experiment == "IV-voltage-log":
        experiment = setups.IVSweep(scale="log", scu_tag=args.scu, mode="voltage", output_name=args.output_name)
        experiment.run()
    elif args.experiment == "lia_readout":
        experiment = setups.LIAMeasurementSetup(output_name=args.output_name, mode="readout")
        experiment.run()
    elif args.experiment == "lia_noise_scan":
        experiment = setups.LIAMeasurementSetup(output_name=args.output_name, mode="scan_noise")
        experiment.run()
    elif args.experiment == "lia_snap_only":
        experiment = setups.LIAMeasurementSetup(
            output_name=args.output_name, mode="snap_only",
            duration=args.duration, sample_interval=args.interval,
        )
        experiment.run()
    else:
        logger.error(f"Unknown experiment: {args.experiment}")
        sys.exit(1)


if __name__ == "__main__":
    main()
