# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this directory.

**Keep [`FSD.md`](FSD.md) up to date.** Whenever ATE drivers, experiments, configs, CLI experiment names or hardware facts change, update `FSD.md` in the same change. `FSD.md` is the single source of truth for hardware connectivity, the signal chain and the PSU-channel / transistor mapping; do not restate those facts here, link to them.

## Setup

The virtualenv lives at the **repo root** (`GMOS-LIA/.venv/`), not inside `ate_lia/`. Dependencies are declared in the root `pyproject.toml` (there is no `requirements.txt`).

```bash
# From repo root (GMOS-LIA/)
python -m venv .venv
source .venv/bin/activate
pip install -e ".[lint,typecheck]"   # extras add ruff and pyright
```

## IMPORTANT: Always use the virtual environment, from the repo root

All dependencies (matplotlib, pyvisa, numpy, etc.) are installed only inside `.venv/`. The system `python`/`python3` will fail with `ModuleNotFoundError`. Run every command below **from the repo root**, so that pytest, ruff and pyright pick up their settings from the root `pyproject.toml`.

**Backend.** Set `PYVISA_LIBRARY=@py` to use the pure-Python `pyvisa-py` backend (no NI-VISA install needed). `run_experiment.sh` and `.mcp.json` both export it. For manual work in a shell, export it yourself, otherwise pyvisa looks for NI-VISA:

```bash
export PYVISA_LIBRARY=@py
```

**Addresses.** Instrument addresses are defined only in `ate_lia/devices.json` (template: `ate_lia/devices.example.json`); the statement is in [`FSD.md`](FSD.md). Do not copy addresses into docs or code; edit `devices.json` for lab-specific addresses.

**`run_experiment.sh`** (repo root, git-ignored, one per machine) is the usual way to run a measurement. It sets `PYTHON=.venv/bin/python`, `CLI=ate_lia/sources/main.py`, exports `PYVISA_LIBRARY=@py`, and then runs **one** experiment as
`"$PYTHON" "$CLI" --experiment <name> --config <toml>`. All other experiment blocks are commented out. To switch experiments, comment out (prefix with `# `) the `echo` + `"$PYTHON"` lines of the active block and uncomment the one wanted. Change parameters by editing the TOML (or copy an `ate_lia/configs/*.example.toml` and point `--config` at the copy); the TOML only needs the fields to override, unknown keys raise `TypeError`. Run from the repo root: `./run_experiment.sh`.

**Manual / interactive equivalents** (run from the repo root):

```bash
# Probe every visible VISA resource and print *IDN? (HP 6624A shows "(no response)")
.venv/bin/python ate_lia/sources/main.py --list_devices

# One experiment without the shell script
.venv/bin/python ate_lia/sources/main.py --experiment lia_snap_sweep --config ate_lia/configs/lia_snap_sweep.toml

# Interactive REPL against the instruments (gmos_repl.py); --log also writes <repo_root>/repl.log
.venv/bin/python ate_lia/sources/main.py --repl [--log]
```

`--output-name <NAME>` sets a custom result filename stem. Results go to `Results/<SetupName>/...`, plots to `Plots/...`.

## Commands

Run from the repo root:

```bash
# Run all tests
.venv/bin/pytest

# Run a single test file / a specific test (including parametrized variants)
.venv/bin/pytest ate_lia/tests/test_bounds.py
.venv/bin/pytest "ate_lia/tests/test_bounds.py::<test_name>[<param-id>]"

# Lint and type check
.venv/bin/ruff check ate_lia
.venv/bin/pyright

# Run an experiment via CLI
.venv/bin/python ate_lia/sources/main.py --experiment <experiment_name> [args]
```

## Architecture

The code is split into layers under `sources/`:

**`ATE/` — Device drivers**
Each file wraps a specific GPIB/VISA instrument. All drivers extend `ATEBase`, which manages the VISA resource lifecycle. Device addresses are loaded from `ate_lia/devices.json`.
- `sr860.py` — Lock-in Amplifier (LIA): frequency, phase, amplitude, DC offset, sensitivity, time constant, filter slope, input settings, snap measurements, auto phase/scale/range. Capture-buffer commands are **not** implemented.
- `b2962a.py` — Source Measure Unit (SCU1/SCU2): voltage/current sourcing, compliance, output/protection, spot measurement, NPLC/aperture.
- `hp6624a.py` — Power Supply (PSU): 4 channels with OCP/OVP (channel roles: `FSD.md`).
- `dso9104a.py` — Oscilloscope: channel/timebase/acquisition setup, free-run digitize, calibrated waveform readback

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
- `HeaterSlopeTable` (`heater_slope_table`): recomputes heater-sensitivity points and slopes (N, σ, settle time, uncertainties) from MCP monitor CSVs; touches no instruments
- `DwellAnalysis` (`dwell_analysis`): quantifies R drift rate and cold-start-to-cold-start operating-point shift from isolated-dwell MCP monitor CSVs; touches no instruments
- `OperatingPointSweep` (`operating_point_sweep`): heater voltage x LIA offset, full SCU1/SCU2 IV curves per point
- `OperatingPointOffsetSweep` (`operating_point_offset_sweep`): lighter variant, one current point per heater voltage x offset
- `LIAOffsetSensitivitySweep` (`lia_offset_sensitivity_sweep`): heater-voltage x SCU-bias x LIA-offset sweep measuring active/blind current sensitivity to a small heater-voltage bump; writes `active.csv`/`blind.csv`
- `DifferentialCalibration` (`lia_differential_calibration`): finds a heater-voltage (PSU ch1/ch3) operating point where LIA X is phase-locked and drift-free; bounded coordinate-descent PSU search driven by the X-vs-time slope; `notes` column narrates every action
- `HeaterResistance` (`heater_resistance`): see below
- `NoiseSpectrumSetup` (`noise_spectrum`): biases the device (SCU1/SCU2 drain, LIA gate offset, heater via `[ate]`), digitizes the differential-amplifier output on the scope (`ATE/dso9104a.py`) and computes its noise PSD/ASD via Welch's method over a configurable `[f_min, f_max]`; writes `timeseries.csv`, `noise_spectrum.csv` (settings preamble — SCU/LIA/Scope/`amplifier_gain` — then the PSD/ASD data) and a log-log ASD `.png`

**Data flow:** `sources/main.py` (CLI) → `setups/` → `ATE/` → GPIB/Ethernet instruments

## MCP server (`gmos-operating-point`)

`sources/mcp_server/server.py` is a FastMCP stdio server wrapping `OperatingPointSession` (`operating_point_session.py`), launched via `.mcp.json` at the repo root (uses `.venv/bin/python`, `PYTHONPATH=ate_lia/sources`, `PYVISA_LIBRARY=@py`). Opening Claude Code at the repo root starts it once the server has been approved on that machine (the approval is stored in the git-ignored `.claude/settings.local.json`). Instruments are opened lazily on the first hardware-touching tool call, so the server merely running does not touch the GPIB bus. Tools return `{"ok": True, ...}` or `{"ok": False, "error_code", "error"}`.

Typical flow: `open_session` → `configure_signal` → `set_offset` → `set_drain_voltage` (SCU1/SCU2) → `set_heater_voltage` (PSU ch1/ch3) → `zero_phase` → `read_r`, or `start_monitoring` / `monitor_status` / `note_event` / `stop_monitoring` (CSV + drift-fit plot) → `close_session`. `configure_signal` uses the default amplitude in `server.py`, capped by `bounds.py`. Other tools: `read_drain_state`, `snapshot_state`, `plot_monitor_session`.

**Hard safety bounds** are plain constants in `sources/mcp_server/bounds.py` (not configurable; out-of-range values are rejected). Read that file for the current limits; do not restate them here. `set_drain_voltage` rolls the setpoint back only when the measured drain current exceeds the upper current bound; a low drain voltage or current keeps the setpoint and is returned in a `warnings` list (also given by `read_drain_state`). Always `close_session` when done (de-energizes the instruments).

Tests: `tests/test_mcp_server_tools.py`, `test_operating_point_session.py`, `test_bounds.py`, `test_continuous_monitor.py`.

## Key Files

- `ate_lia/devices.json` — VISA addresses for all instruments (edit this for lab-specific configuration; template: `ate_lia/devices.example.json`)
- `FSD.md` — Functional Specifications Document: hardware connectivity, signal chain, PSU-channel / transistor mapping, device IDN strings, ATE APIs, experiment descriptions
- `../run_experiment.sh` — local, git-ignored helper that runs one experiment via the CLI with `PYVISA_LIBRARY=@py` (create it per machine; the manual commands above do the same)
- `configs/*.example.toml` — one example config per experiment

## Heater resistance experiment

`heater_resistance` (`setups/heater_resistance.py`, config `HeaterResistanceConfig`, example `configs/heater_resistance.example.toml`) sweeps PSU ch1/ch3 with ESD/fan on, averages `n_samples` readings (`sample_interval` apart) per point, repeats `n_repeats` times, writes `Results/HeaterResistanceSetup/<session>/heater_resistance.csv` + `fit_summary.csv`, and plots I-V with linear fit, R^2 and MSE error lines to `Plots/`. To run via `run_experiment.sh`: uncomment the `heater_resistance` block (comment out any other active experiment) and edit the TOML (or point `--config` at a copy).
