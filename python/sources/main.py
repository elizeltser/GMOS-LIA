import argparse
import logging
import os
import sys
from dataclasses import replace

# Add python/sources/ to path so ATE and setups are importable as top-level packages
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import setups
from config import (
    ATEConfig,
    IVSweepConfig,
    LIADigestSweepConfig,
    LIADriftEvolutionConfig,
    LIAGasResponseConfig,
    LIAReadoutConfig,
    LIASnapConfig,
    load_config,
)
from gmos_repl import run_repl
from plotting import (
    LIADiffSweepScatterCompiler,
    LIAFrequencyResponseCompiler,
    LIAPlotCompiler,
    LIASnapDigest,
    LIASweepScatterCompiler,
    NoiseEvalCompiler,
    PlotCompiler,
)
from visa_enumeration import list_devices

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# experiment name -> (setup class, config dataclass or None, constructor kwargs,
# config field overrides forced by this experiment name regardless of --config)
_EXPERIMENTS = {
    "IV-voltage-lin": (setups.IVSweep, IVSweepConfig, {}, {"scale": "linear"}),
    "IV-voltage-log": (setups.IVSweep, IVSweepConfig, {}, {"scale": "log"}),
    "lia_readout":    (setups.LIAMeasurementSetup, LIAReadoutConfig, {"mode": "readout"}, {}),
    "lia_noise_scan": (setups.LIAMeasurementSetup, LIAReadoutConfig, {"mode": "scan_noise"}, {}),
    "lia_snap_only":  (setups.LIAMeasurementSetup, LIASnapConfig, {"mode": "snap_only"}, {}),
    "lia_snap_sweep": (setups.LIAMeasurementSetup, LIASnapConfig, {"mode": "snap_sweep"}, {}),
    "lia_gas_response": (setups.LIAMeasurementSetup, LIAGasResponseConfig, {"mode": "gas_response"}, {}),
    "lia_digest_sweep": (setups.LIADigestSweep, LIADigestSweepConfig, {}, {}),
    "lia_drift_evolution": (setups.LIADriftEvolution, LIADriftEvolutionConfig, {}, {}),
}


def main():
    parser = argparse.ArgumentParser(description="GMOS LIA Experiment Runner")
    parser.add_argument("--experiment", "-e", help="Experiment name")
    parser.add_argument("--config", "-c", metavar="TOML",
                        help="Path to a TOML file with [ate] and [experiment] tables "
                             "overriding this experiment's parameters")
    parser.add_argument("--list_devices", action="store_true",
                        help="List all available VISA resources and exit")
    parser.add_argument("--repl", action="store_true",
                        help="Enter interactive REPL")
    parser.add_argument("--log", action="store_true",
                        help="With --repl: also log to <repo_root>/repl.log")
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
    parser.add_argument("--lia-baseline", action="store_true",
                        help="With --lia-digest: treat as a baseline run and overlay a "
                             "linear R-drift fit with the estimated drift rate")
    parser.add_argument("--lia-sweep-scatter", nargs="+", metavar="CSV",
                        help="LIA snap CSVs to scatter against a swept parameter")
    parser.add_argument("--lia-diff-baseline", nargs="+", metavar="CSV",
                        help="Baseline (e.g. nogas) LIA snap CSVs for a difference sweep")
    parser.add_argument("--lia-diff-signal", nargs="+", metavar="CSV",
                        help="Signal (e.g. gas) LIA snap CSVs; subtracted against --lia-diff-baseline")
    parser.add_argument("--sweep-param", choices=["freq", "offset", "sr560_amp"],
                        help="Parameter swept across --lia-sweep-scatter inputs")
    parser.add_argument("--lia-freq-response", nargs="+", metavar="CSV",
                        help="LIA digest (or raw snap) CSVs across a frequency sweep; "
                             "produces separate R, theta, and R-drift vs frequency plots")
    parser.add_argument("--phase-shift-deg", type=float, default=0.0,
                        help="With --lia-freq-response: constant phase offset (deg) "
                             "added to every point in the theta plot")
    parser.add_argument("--x-scale", choices=["linear", "log"], default="linear",
                        help="X-axis scale (default: linear)")
    parser.add_argument("--y-scale", choices=["linear", "log"], default="linear",
                        help="Y-axis scale (default: linear)")
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
        digest = LIASnapDigest(args.lia_digest, baseline=args.lia_baseline)
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

    if args.lia_freq_response:
        out_paths = LIAFrequencyResponseCompiler(
            args.lia_freq_response, out_name=args.output_name,
            phase_shift_deg=args.phase_shift_deg,
        ).compile()
        for out_path in out_paths:
            print(f"Plot saved to: {out_path}")
        return

    if not args.experiment:
        parser.error("--experiment / -e is required unless --list_devices, --repl, or --compile-2d-plot is used")

    if args.experiment not in _EXPERIMENTS:
        logger.error(f"Unknown experiment: {args.experiment}")
        sys.exit(1)

    logger.info(f"Starting experiment: {args.experiment}")

    setup_cls, config_cls, ctor_kwargs, config_overrides = _EXPERIMENTS[args.experiment]

    ate_config = ATEConfig()
    experiment_config = config_cls() if config_cls else None
    if args.config:
        ate_config, loaded_config = load_config(args.config, config_cls)
        if loaded_config is not None:
            experiment_config = loaded_config
    if experiment_config is not None and config_overrides:
        experiment_config = replace(experiment_config, **config_overrides)

    kwargs = dict(ctor_kwargs, output_name=args.output_name, ate_config=ate_config)
    if experiment_config is not None:
        kwargs["config"] = experiment_config

    experiment = setup_cls(**kwargs)
    experiment.run()


if __name__ == "__main__":
    main()
