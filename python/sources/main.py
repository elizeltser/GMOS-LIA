#!/usr/bin/env python3
"""
Main entry point for GMOS LIA automation.
CLI to run experiments.
"""

import argparse
import os
import sys

import pyvisa

from . import setups
from .setups import SetupBase

# Add sources to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sources'))

def main():
    parser = argparse.ArgumentParser(description='GMOS LIA Experiment Runner')
    parser.add_argument('--experiment', '-e', required=True, help='Experiment name')
    parser.add_argument('--config', '-c', help='Config file path')
    # Add other args as needed

    args = parser.parse_args()

    # Run the experiment
    experiment: SetupBase | None = None
    if args.experiment == 'IV-voltage-lin':
        experiment = setups.IVSweep(scale='linear', mode='voltage')
        experiment.run()
    elif args.experiment == 'IV-current-log':
        experiment = setups.IVSweep(scale='log', mode='current')
        experiment.run()
    elif args.experiment == 'SG-pulse-burst':
        experiment = setups.SignalPulseBurst()
        experiment.run()
    elif args.experiment == 'noise-measurement':
        experiment = setups.NoiseMeasurement()
        experiment.run()
    else:
        print(f"Unknown experiment: {args.experiment}")
        sys.exit(1)

if __name__ == '__main__':
    main()
