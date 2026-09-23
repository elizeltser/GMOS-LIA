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
    DifferentialCalibrationConfig,
    DwellAnalysisConfig,
    HeaterResistanceConfig,
    HeaterSlopeTableConfig,
    IVSweepConfig,
    LIADigestSweepConfig,
    LIADriftEvolutionConfig,
    LIAGasResponseInteractiveConfig,
    LIAOffsetSensitivitySweepConfig,
    LIAReadoutConfig,
    LIASnapConfig,
    OperatingPointOffsetSweepConfig,
    OperatingPointSweepConfig,
    load_config,
)
from gmos_repl import run_repl
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
    "lia_readout": (
        setups.LIAMeasurementSetup,
        LIAReadoutConfig,
        {"mode": "readout"},
        {},
    ),
    "lia_noise_scan": (
        setups.LIAMeasurementSetup,
        LIAReadoutConfig,
        {"mode": "scan_noise"},
        {},
    ),
    "lia_snap_only": (
        setups.LIAMeasurementSetup,
        LIASnapConfig,
        {"mode": "snap_only"},
        {},
    ),
    "lia_snap_sweep": (
        setups.LIAMeasurementSetup,
        LIASnapConfig,
        {"mode": "snap_sweep"},
        {},
    ),
    "lia_gas_response_interactive": (
        setups.LIAMeasurementSetup,
        LIAGasResponseInteractiveConfig,
        {"mode": "gas_response_interactive"},
        {},
    ),
    "lia_digest_sweep": (setups.LIADigestSweep, LIADigestSweepConfig, {}, {}),
    "heater_slope_table": (setups.HeaterSlopeTable, HeaterSlopeTableConfig, {}, {}),
    "dwell_analysis": (setups.DwellAnalysis, DwellAnalysisConfig, {}, {}),
    "lia_drift_evolution": (setups.LIADriftEvolution, LIADriftEvolutionConfig, {}, {}),
    "operating_point_sweep": (
        setups.OperatingPointSweep,
        OperatingPointSweepConfig,
        {},
        {},
    ),
    "operating_point_offset_sweep": (
        setups.OperatingPointOffsetSweep,
        OperatingPointOffsetSweepConfig,
        {},
        {},
    ),
    "lia_offset_sensitivity_sweep": (
        setups.LIAOffsetSensitivitySweep,
        LIAOffsetSensitivitySweepConfig,
        {},
        {},
    ),
    "lia_differential_calibration": (
        setups.DifferentialCalibration,
        DifferentialCalibrationConfig,
        {},
        {},
    ),
    "heater_resistance": (
        setups.HeaterResistanceSetup,
        HeaterResistanceConfig,
        {},
        {},
    ),
}


def main():
    parser = argparse.ArgumentParser(description="GMOS LIA Experiment Runner")
    parser.add_argument("--experiment", "-e", help="Experiment name")
    parser.add_argument(
        "--config",
        "-c",
        metavar="TOML",
        help="Path to a TOML file with [ate] and [experiment] tables "
        "overriding this experiment's parameters",
    )
    parser.add_argument(
        "--list_devices",
        action="store_true",
        help="List all available VISA resources and exit",
    )
    parser.add_argument("--repl", action="store_true", help="Enter interactive REPL")
    parser.add_argument(
        "--log",
        action="store_true",
        help="With --repl: also log to <repo_root>/repl.log",
    )
    parser.add_argument(
        "--output-name",
        metavar="NAME",
        help="Custom result filename stem (no extension); "
        "omit for auto date-stamped name",
    )
    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return

    if args.repl:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        log_path = os.path.join(repo_root, "repl.log") if args.log else None
        run_repl(log_path=log_path)
        return

    if not args.experiment:
        parser.error(
            "--experiment / -e is required unless --list_devices or --repl is used"
        )

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
