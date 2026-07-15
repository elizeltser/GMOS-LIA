# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this directory.

## Setup

The virtualenv lives at the **repo root** (`GMOS-LIA/.venv/`), not inside `python/`.

```bash
# From repo root (GMOS-LIA/)
python -m venv .venv
source .venv/bin/activate
cd python
pip install -e .
pip install -r ./requirements.txt
```

## IMPORTANT: Always use the virtual environment

All dependencies (matplotlib, pyvisa, numpy, etc.) are installed only inside `.venv/`. The system `python`/`python3` will fail with `ModuleNotFoundError`. The venv is one level up from this directory — always use `../.venv/bin/python` (or activate first).

```bash
# Correct — use venv Python directly (from python/ directory)
../.venv/bin/python sources/main.py --experiment <experiment_name>
../.venv/bin/pytest tests/
../.venv/bin/ruff check .
../.venv/bin/pyright .

# Or activate once from the repo root and use bare commands
source ../.venv/bin/activate
python sources/main.py ...
```

## Commands

```bash
# Run all tests
../.venv/bin/pytest tests/

# Run a single test file
../.venv/bin/pytest tests/test_iv_sweeps.py

# Run a specific test (including parametrized variants)
../.venv/bin/pytest tests/test_iv_sweeps.py::test_linear_iv_sweep
../.venv/bin/pytest tests/test_iv_sweeps.py::test_linear_iv_sweep[0-1-0.1]

# Lint
../.venv/bin/ruff check .

# Type check
../.venv/bin/pyright .

# Run an experiment via CLI
../.venv/bin/python sources/main.py --experiment <experiment_name> [args]
```

## Architecture

The code is split into two layers under `sources/`:

**`ATE/` — Device drivers**
Each file wraps a specific GPIB/VISA instrument. All drivers extend `ATEBase`, which manages the VISA resource lifecycle. Device addresses are loaded from `devices.json` in this directory.
- `sr860.py` — Lock-in Amplifier (LIA): frequency, phase, sensitivity, snap measurements
- `b2962a.py` — Source Measure Unit (SCU): voltage/current sourcing with compliance limits
- `hp6624a.py` — Power Supply (PSU): 4-channel with OCP/OVP protection
- `dso9104a.py` — Oscilloscope (stub)

**`setups/` — Experiment implementations**
Each experiment extends `SetupBase`, which provides:
- `@setup_ate` decorator for automatic device setup/teardown
- Results directory management
- CSV data saving utilities

Concrete experiments (CLI `--experiment` names in parentheses):
- `IVSweep` (`IV-voltage-lin`, `IV-voltage-log`): Voltage sweep (linear or log scale) using SCU
- `LIAMeasurementSetup`: the main working path. Modes:
  - `lia_snap_only`: snap X/Y/R at fixed intervals for a duration (assumes LIA already configured)
  - `lia_snap_sweep`: snap capture at each reference frequency, one CSV per frequency
  - `lia_readout`, `lia_noise_scan`: configure the LIA/SCUs and read out (needs attention)
  - `lia_gas_response`: manually-gated baseline/gas-exposure capture for actual gas dosing runs. The operator presses Enter three times (setup settled, gas inserted, stop) while sampling continues uninterrupted; writes `baseline.csv` and `gas.csv` per session folder
- `LIADriftEvolution` (`lia_drift_evolution`): analyzes how the R-drift rate evolves across an already-captured sweep folder's digest files (drift-of-drift + exponential fit); touches no instruments

Experimental / work-in-progress (not on the supported CLI path):
- `NoiseMeasurement`: multi-threaded data capture from LIA (VISA thread-safety caveats)

**Data flow:** `sources/main.py` (CLI) → `setups/` → `ATE/` → GPIB/Ethernet instruments

## Key Files

- `devices.json` — VISA addresses for all instruments (edit this for lab-specific configuration)
- `FSD.md` — Functional Specifications Document: hardware connectivity, device IDN strings, experiment descriptions
