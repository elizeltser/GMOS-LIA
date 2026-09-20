# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this directory.

**Keep [`FSD.md`](FSD.md) up to date.** Whenever ATE drivers, experiments, configs, CLI experiment names or hardware facts change, update `FSD.md` in the same change. `FSD.md` is the single source of truth for hardware connectivity, the signal chain and the PSU-channel / transistor mapping; do not restate those facts here, link to them.

## Setup

The virtualenv lives at the **repo root** (`GMOS-LIA/.venv/`), not inside `python/`. Dependencies are declared in the root `pyproject.toml` (there is no `requirements.txt`).

```bash
# From repo root (GMOS-LIA/)
python -m venv .venv
source .venv/bin/activate
pip install -e .
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

## VISA and running experiments

**Backend.** Set `PYVISA_LIBRARY=@py` to use the pure-Python `pyvisa-py` backend (no NI-VISA install needed). `run_experiment.sh` and `.mcp.json` both export it. For manual work in a shell, export it yourself, otherwise pyvisa looks for NI-VISA:

```bash
export PYVISA_LIBRARY=@py
```

**Addresses.** `python/devices.json` maps tags (`LIA`, `SCU1`, `SCU2`, `PSU`, `Scope`) to VISA resource strings (GPIB or `TCPIP::<ip>::INSTR`). Edit it for lab-specific addresses.

**`run_experiment.sh`** (repo root) is the standard way to run a measurement. It sets `PYTHON=.venv/bin/python`, `CLI=python/sources/main.py`, exports `PYVISA_LIBRARY=@py`, and then runs **one** experiment as
`"$PYTHON" "$CLI" --experiment <name> --config <toml>`. All other experiment blocks are commented out. To switch experiments, comment out (prefix with `# `) the `echo` + `"$PYTHON"` lines of the active block and uncomment the one wanted. Change parameters by editing the TOML (or copy an `python/configs/*.example.toml` and point `--config` at the copy); the TOML only needs the fields to override, unknown keys raise `TypeError`. Run from the repo root: `./run_experiment.sh`.

**Manual / interactive equivalents** (run from the repo root):

```bash
# Probe every visible VISA resource and print *IDN? (HP 6624A shows "(no response)")
.venv/bin/python python/sources/main.py --list_devices

# One experiment without the shell script
.venv/bin/python python/sources/main.py --experiment lia_snap_sweep --config python/configs/lia_snap_sweep.toml

# Interactive REPL against the instruments (gmos_repl.py); --log also writes <repo_root>/repl.log
.venv/bin/python python/sources/main.py --repl [--log]
```

`--output-name <NAME>` sets a custom result filename stem. Results go to `Results/<SetupName>/...`, plots to `Plots/...`.

## Commands

```bash
# Run all tests
../.venv/bin/pytest tests/

# Run a single test file
../.venv/bin/pytest tests/test_bounds.py

# Run a specific test (including parametrized variants)
../.venv/bin/pytest tests/test_operating_point_session.py::<test_name>
../.venv/bin/pytest "tests/test_bounds.py::<test_name>[<param-id>]"

# Lint
../.venv/bin/ruff check .

# Type check
../.venv/bin/pyright .

# Run an experiment via CLI
../.venv/bin/python sources/main.py --experiment <experiment_name> [args]
```

## Architecture

The code is split into layers under `sources/`:

**`ATE/` — Device drivers**
Each file wraps a specific GPIB/VISA instrument. All drivers extend `ATEBase`, which manages the VISA resource lifecycle. Device addresses are loaded from `python/devices.json`.
- `sr860.py` — Lock-in Amplifier (LIA): frequency, phase, amplitude, DC offset, sensitivity, time constant, filter slope, input settings, snap measurements, auto phase/scale/range. Capture-buffer commands are **not** implemented.
- `b2962a.py` — Source Measure Unit (SCU1/SCU2): voltage/current sourcing, compliance, output/protection, spot measurement, NPLC/aperture.
- `hp6624a.py` — Power Supply (PSU): 4 channels with OCP/OVP; ch2 = ESD protection, ch4 = fan, ch1/ch3 = heaters.
- `dso9104a.py` — Oscilloscope (stub)

**`setups/` — Experiment implementations**
Each experiment extends `SetupBase`, which provides:
- `@setup_ate` decorator for automatic device setup/teardown
- Results directory management
- CSV data saving utilities

**`config.py`** holds one typed dataclass per experiment (defaults = former hard-coded values), loaded from TOML by `--config`.

**`mcp_server/`** — MCP tool server for interactive operating-point work (see below).

Experiments (CLI `--experiment` names in parentheses; authoritative map is `_EXPERIMENTS` in `sources/main.py`):
- `IVSweep` (`IV-voltage-lin`, `IV-voltage-log`): Voltage sweep (linear or log scale) using an SCU
- `LIAMeasurementSetup` (`setups/lia_setup.py`), modes:
  - `lia_snap_only`: snap X/Y/R at fixed intervals for a duration (assumes LIA already configured)
  - `lia_snap_sweep`: snap capture at each reference frequency, one CSV per frequency
  - `lia_readout`, `lia_noise_scan`: configure the LIA/SCUs and read out (needs attention)
  - `lia_gas_response_interactive`: operator-marked gas-dosing run at a fixed (temperature, frequency) operating point. Enter marks an event, Esc stops; writes one `gas_response.csv` (`index`/`event` columns) plus a time-series plot
- `LIADigestSweep` (`lia_digest_sweep`): digests already-captured snap CSVs into R/theta/drift-vs-frequency plots; touches no instruments
- `LIADriftEvolution` (`lia_drift_evolution`): R-drift rate evolution across a captured sweep's digest files; touches no instruments
- `OperatingPointSweep` (`operating_point_sweep`): heater voltage x LIA offset, full SCU1/SCU2 IV curves per point
- `OperatingPointOffsetSweep` (`operating_point_offset_sweep`): lighter variant, one current point per heater voltage x offset
- `LIAOffsetSensitivitySweep` (`lia_offset_sensitivity_sweep`): heater-voltage x SCU-bias x LIA-offset sweep measuring active/blind current sensitivity to a small heater-voltage bump; writes `active.csv`/`blind.csv`
- `DifferentialCalibration` (`lia_differential_calibration`): finds a heater-voltage (PSU ch1/ch3) operating point where LIA X is phase-locked and drift-free; bounded coordinate-descent PSU search driven by the X-vs-time slope; `notes` column narrates every action
- `HeaterResistance` (`heater_resistance`): see below

**Data flow:** `sources/main.py` (CLI) → `setups/` → `ATE/` → GPIB/Ethernet instruments

## MCP server (`gmos-operating-point`)

`sources/mcp_server/server.py` is a FastMCP stdio server wrapping `OperatingPointSession` (`operating_point_session.py`), launched via `.mcp.json` at the repo root (uses `.venv/bin/python`, `PYTHONPATH=python/sources`, `PYVISA_LIBRARY=@py`). Opening Claude Code in this repo auto-connects. Instruments are opened lazily on the first hardware-touching tool call, so the server merely running does not touch the GPIB bus. Tools return `{"ok": True, ...}` or `{"ok": False, "error_code", "error"}`.

Typical flow: `open_session` → `configure_signal` → `set_offset` → `set_drain_voltage` (SCU1/SCU2) → `set_heater_voltage` (PSU ch1/ch3) → `zero_phase` → `read_r`, or `start_monitoring` / `monitor_status` / `note_event` / `stop_monitoring` (CSV + drift-fit plot) → `close_session`. `configure_signal` defaults to a 5 mV amplitude (hard limit 7 mV). Other tools: `read_drain_state`, `snapshot_state`, `plot_monitor_session`.

**Hard safety bounds** (`mcp_server/bounds.py`, plain constants, not configurable; out-of-range values are rejected): LIA offset 0.87–1.1 V, LIA amplitude ≤ 7 mV, heater 2.85–3.1 V, drain current 7–10 µA, drain voltage Vd ≥ 120 mV (Vd = Vscu − 330 kΩ · Iscu). `set_drain_voltage` rolls the setpoint back if the measured result violates the current/Vd window. Always `close_session` when done (de-energizes the instruments).

Tests: `tests/test_mcp_server_tools.py`, `test_operating_point_session.py`, `test_bounds.py`, `test_continuous_monitor.py`.

## Key Files

- `python/devices.json` — VISA addresses for all instruments (edit this for lab-specific configuration)
- `FSD.md` — Functional Specifications Document: hardware connectivity, signal chain, PSU-channel / transistor mapping, device IDN strings, ATE APIs, experiment descriptions
- `../run_experiment.sh` — runs one experiment via the CLI with `PYVISA_LIBRARY=@py`
- `configs/*.example.toml` — one example config per experiment

## Heater resistance experiment

`heater_resistance` (`setups/heater_resistance.py`, config `HeaterResistanceConfig`, example `configs/heater_resistance.example.toml`) sweeps PSU ch1/ch3 with ESD/fan on, averages `n_samples` readings (`sample_interval` apart) per point, repeats `n_repeats` times, writes `Results/HeaterResistanceSetup/<session>/heater_resistance.csv` + `fit_summary.csv`, and plots I-V with linear fit, R^2 and MSE error lines to `Plots/`. To run via `run_experiment.sh`: uncomment the `heater_resistance` block (comment out any other active experiment) and edit the TOML (or point `--config` at a copy).
