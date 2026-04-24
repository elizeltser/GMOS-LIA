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
- `hp8116a.py` — Signal Generator (SG): frequency sweep, pulse/burst modes
- `dso9104a.py` — Oscilloscope (stub)

**`setups/` — Experiment implementations**
Each experiment extends `SetupBase`, which provides:
- `@setup_ate` decorator for automatic device setup/teardown
- Results directory management
- CSV data saving utilities

Concrete experiments:
- `IVSweep`: Voltage/current sweep (linear or log scale) using SCU
- `NoiseMeasurement`: Multi-threaded 100 Hz data capture from LIA
- `SignalPulseBurst`: Frequency sweep combining LIA, SCU bias, and SG signal

**Data flow:** `sources/main.py` (CLI) → `setups/` → `ATE/` → GPIB/Ethernet instruments

## Key Files

- `devices.json` — VISA addresses for all instruments (edit this for lab-specific configuration)
- `FSD.md` — Functional Specifications Document: hardware connectivity, device IDN strings, experiment descriptions
