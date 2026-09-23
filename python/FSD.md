# GMOS LIA - Functional Specifications Document

This file is an in-depth full functional specifications documentation document describing the requirements from a hardware setup designed to test and measure the GMOS gas sensor device, mainly for research purpose.

## Introduction

The GMOS gas sensor is a CMOS-SOI-MEMS device based around the TMOS temperature sensor. The sensor was designed and developed in Technion institute of technology in Israel, by Prof. emeritus Yael Nemirovsky and her research team.
This document is compiled and written by Eli Zeltser - for Msc work and for auto-generation of the code for the setup hardware control.
This document will include:

- Definition of the hardware connectivity for the various experiments and evaluations of the GMOS device.
- Detailed description of the experiments for each hardware connection.
- Definition of the project structure as well as the coding conventions, specific implementation details and code examples.
- Analysis of the results.

> This document will be further written as the repository grows it may not represent its content at any given time.

## Installation & Prerequisites

For the correct usage of this project one must make sure the following programs are installed:

- **Python** version at least 3.13
- **NI-VISA** driver for GPIB devices (or **pyvisa-py** as a pure-Python alternative — no driver installation required, included as a project dependency)

To install the project on the PC one must run the following commands:

```shell
python -m venv .venv
.\.venv\Scripts\activate
# for Linux or Mac that will be `source ./.venv/bin/activate`
git clone https://github.com/elizeltser/GMOS-LIA.git
cd GMOS-LIA
pip install .
```

## List of Acronyms

| Acronym | Meaning |
| ------------- | :-------------: |
| GMOS | Gas MOS |
| LIA | Lock in amplifier |

## Hardware Connectivity

The hardware setup for the GMOS experimentation is one of the following:

1. Single ended connection
2. Bridge connection

In addition to the above experiment use-cases, there are several additional useful setups that are useful for general usage and setup debugging:

1. I-V sweep

## Definitions for the GMOS

Each DUT chip contains 6 GMOS devices, two of which have slightly different heat properties thus they are never used. The remaining four devices are divided for **active and blind** pairs. A bridge connection always tests pairs of active-blind, while single ended connection measures only one device at a time. The DUT chip exposes all of the pins for each GMOS device as well as dedicated pins for GND and VDD, which must be powered with 5v between them whenever the DUT is used (essential for ESD protection and proper operation). Apart from the unrelated pins mentioned previously, the DUT chip has the following list of pins **for each GMOS device** (i.e multiplied by 6):

- GMOS drain
- GMOS source
- GMOS gate
- Heater positive
- Heater negative

The GMOS is always connected with the **3T method**: gate and drain are driven independently (gate by the LIA DC offset, drain by an SCU through a series resistor, see [Signal Chain](#signal-chain)).

### Signal Chain

- **LIA DC offset (`SOFF`)** is the GMOS **gate voltage (DC)**; it is shared by both transistors of a pair.
- **LIA amplitude (`SLVL`)** is the amplitude of the (AC) signal applied on top of that offset.
- Each **drain** is connected to a resistor of approximately **330 kΩ**, whose other end is connected to an **SCU channel** (SCU1 or SCU2). The SCU sets the DC drain bias and measures the drain current.
- The two **drains** also feed the two inputs of a **differential amplifier (Stanford Research SR560)**. Its output drives the **SR860 LIA input**.
- All stages are **AC coupled**.
- **SR560 settings:** gain of 20, band-pass filter with 6 dB/oct roll-off on both sides, between 300 Hz and 1 kHz.

### PSU Channel / Transistor Mapping

**Single point of truth for which heater affects which transistor.** Code must import `HEATER_CHANNEL_FOR_SCU` from `python/sources/config.py`; do not restate the mapping elsewhere.

| PSU channel | Heats device | Measured by | Role |
| :---: | :---: | :---: | :---: |
| 1 | transistor connected to SCU1 | SCU1 | active |
| 3 | transistor connected to SCU2 | SCU2 | blind / reference |
| 2 | (DUT VDD/GND, 5 V ESD protection) | - | - |
| 4 | (fan) | - | - |

*Validated on hardware through the `gmos-operating-point` MCP server:* LIA offset 1.0 V, amplitude 5 mV @ 518 Hz, SCU set to 2.5–3.2 V, heaters at 2.9 V (the MCP hard lower bound is 2.8 V, so the 2.5 V originally proposed was not used).

- All heaters off (~0 V): SCU1 current 0 A, SCU2 current 1e-7 A at 2.5 V. Both are far below the 7 µA expected of a conducting device.
- PSU ch1 on only: SCU1 conducts (Vd ≈ 0 V, so the current is resistor-limited, ≈ Vscu/330 kΩ ≈ 7.6 µA at 2.5 V); SCU2 stays at 1e-7 A.
- PSU ch3 also on: SCU2 conducts fully (Vd ≈ -5 mV at 2.8 V), as SCU1 did.

Note a fully-heated device at 2.9 V cannot satisfy the Vd >= 110 mV target window. The MCP tool `set_drain_voltage` therefore keeps the setpoint and reports a `warnings` entry when Vd is low or the current is below 7 µA, so the operating point can be explored; only a drain current above 10 µA is rolled back. `read_drain_state` reports the same warnings. The mapping evidence above comes from the current readings quoted in the earlier rejection messages.

## Automatic Test Equipment

The hardware components of the setup for the GMOS analysis are high-end test and measurement devices, here is a full list of the devices that are all connected in the setup:

- SR860 Lock in amplifier
- Keysight b2962a source and measurement
- HP 6624 power supply
- Keysight DSO9104A Infiniium scope

All of the devices GPIB or IP addresses are stored in the `devices.json`.
Here is a table with additional information:

| Device | Tag | Address | IDN string |
| ------------- | :-------------: | :-------------: | ------------- |
| **SR860** | LIA | `TCPIP::132.68.54.194::INSTR` | "Stanford_Research_Systems,SR860,003693,V1.51\n" |
| **Keysight DSO9104A** | Scope | `TCPIP::132.68.54.234::INSTR` | "KEYSIGHT TECHNOLOGIES,DSO9104A,MY53130118,06.00.00901\n" |
| **Keysight B2962A** | SCU1 | `GPIB0::22::INSTR` | "Keysight Technologies,B2962A,MY52350661,2.2.1744.8725\n" |
| **Keysight B2962A** | SCU2 | `GPIB0::23::INSTR` | "Keysight Technologies,B2962A,MY52350537,2.0.1613.9020\n" |
| **HP 6624a** | PSU | `GPIB0::14::INSTR` | "\n" |

> Not all of the equipment is used for all the setup scenarios.
> HP devices are old and have no `IDN` string.

## Bridge connection

In the bridge connection, two GMOS devices are connected exactly in the **same way they are connected in the single ended connection** (each transistor is connected in series to the GMOS drain-gate). The resistors on their other side (which is not facing the drains) are shorted together and are the top node of the bridge.

## Project Structure

The automation work included in this repository should be written in **Python**. This will make the tests and scripts that control the setup easier to write. The python program will have two possible entry points, either **regular python scripting**, or **pytest** that can be very useful with its fixtures and parametrization of tests. Project may require additional hardware components such as MCUs or FPGAs.
> While *currently* not in use, we may require generating low-level communication signals. The code of those components will be stored in their own separate folder from the project to help organize the files.

```shell
/
├── .venv/                # Local Python virtual environment
├── Python/
│   ├── main.py           # Application entry point
│   ├── sources/          # Core ATE (Automatic Test Equipment) logic
│   │   ├── ATE/          # Hardware wrappers for GPIB & test devices
│   │   └── plotting/     # Modules related to measurement output port-processing
│   │   └── setups/       # Definitions for experiment scenarios
│   └── testing/          # Unit tests and hardware mocks (TBD)
├── Firmware/
│   └── TBD/              # Embedded source code and build files
├── Results/              # Data logs and experiment output (Org TBD)
├── devices.json          # Hardware configuration and addresses
├── pyproject.toml        # Ruff, Pyright, and dependency config
└── .gitignore            # Files excluded from version control
```

### Python Modules

Since we do not desire to utilize the low level operational commands directly, we will create python wrapperes that abstracts away the existing ATE APIs (mostly GPIB commands and streaming data in special cases such as for the LIA and the scope).  
Additionaly under the `python\sources\setups\` directory, the actual implementation of the experiment will reside.
The **main entry point for the project** (i.e `main.py`) will implement a CLI that will receive the name of the experiment as an argument and will implement the experiment. For example when executing:

```shell
python sources/main.py --experiment IV-voltage-lin
# Executes linear Voltage force, current measure sweep, with start, stop, step triplet hard-coded in setup init.
python sources/main.py --experiment lia_snap_sweep
# Here all of the configurations are hardcoded in the setup init.
```

> pytest entry point TBD...

#### CLI Reference

Run from the repo root with `python python/sources/main.py <args>`.

| Argument | Short | Description |
| --- | :---: | --- |
| `--experiment <name>` | `-e` | Run a named experiment. Required unless `--list_devices` or `--repl` is used. Valid names: `IV-voltage-lin`, `IV-voltage-log`, `lia_readout`, `lia_noise_scan`, `lia_snap_only`, `lia_snap_sweep`, `lia_gas_response_interactive`, `lia_digest_sweep`, `lia_drift_evolution`, `operating_point_sweep`, `operating_point_offset_sweep`, `lia_offset_sensitivity_sweep`, `lia_differential_calibration`, `heater_resistance`, `heater_slope_table`, `dwell_analysis`. The authoritative list is `_EXPERIMENTS` in `python/sources/main.py`. |
| `--config <path>` | `-c` | Path to a TOML file with `[ate]` and `[experiment]` tables overriding the selected experiment's parameters. See [Experiment Configuration Files](#experiment-configuration-files) below. |
| `--list_devices` | — | Probe all visible VISA resources and print a summary grouped by interface type (GPIB, TCPIP, USB, Serial). For each resource the VISA address string, interface-specific details (GPIB primary address / IP host / USB serial number), and the `*IDN?` response are shown. Devices that do not respond to IDN (e.g. HP 6624A) display `(no response)`. |
| `--repl` | — | Enter an interactive REPL instead of running an experiment (see `gmos_repl.py`). |
| `--log` | — | With `--repl`: also log the session to `<repo_root>/repl.log`. |
| `--output-name <NAME>` | — | Custom result filename stem (no extension) for the running experiment; omit for an auto date-stamped name. |

Example output of `--list_devices`:

```
==================================================
  VISA Device Discovery  (4 resource(s) found)
==================================================

[GPIB]
  GPIB0::22::INSTR
    Board   : GPIB0   Primary address: 22
    IDN     : Keysight Technologies,B2962A,MY52350661,2.2.1744.8725

[TCPIP]
  TCPIP0::132.68.54.194::inst0::INSTR
    Host    : 132.68.54.194
    IDN     : Stanford_Research_Systems,SR860,003693,V1.51
```

#### Experiment Configuration Files

Each experiment's parameters live in a typed dataclass (`python/sources/config.py`), whose field defaults reproduce the value that used to be hard-coded for that experiment. `--config <path>` points at a TOML file with up to two tables:

- `[ate]` — overrides `ATEConfig` (ESD/fan voltage-current, optional `heater1`/`heater3` `HeaterConfig` sub-tables, `debug_device_io`).
- `[experiment]` — overrides the config dataclass selected for `--experiment <name>` (e.g. `LIASnapConfig` for `lia_snap_sweep`, `OperatingPointSweepConfig` for `operating_point_sweep`).

A TOML file only needs to name the fields it wants to change; unspecified fields keep their dataclass default. Unknown keys raise `TypeError` at load time rather than being silently ignored. Nested structures are supported:

- **Nested dataclasses** — `heater1`/`heater3` (`HeaterConfig`) accept a sub-table that layers onto that nested dataclass's own defaults.
- **Sweep sub-tables** — fields that hold a swept vector (e.g. `frequencies`, `scu_voltages`, `heater_voltages`, `lia_offsets`) accept either a literal list or a `Sweep` sub-table (`start`, `stop`, `num`, `scale` = `"linear"`/`"log"`/`"reverse-linear"`), expanded via `numpy.linspace`/`logspace` at load time.
- **Enum fields** — LIA/SCU instrument settings (e.g. `sensitivity`, `filter_slope`, `time_constant`, `input_coupling`, `input_source`, `input_range`) accept the enum member name as a string, e.g. `sensitivity = "MV500"`.

Example (`python/configs/lia_snap_sweep.toml`-style):

```toml
[ate]
debug_device_io = true

[ate.heater1]
voltage = 2.7
current = 0.05

[experiment]
duration = 30.0
configure_instruments = true

[experiment.frequencies]
start = 0.1
stop = 40.0
num = 10
scale = "log"
```

Example config files for each experiment live under `python/configs/`.

#### `ATE` Implementation Details

ATE device wrappers will be written in the `python\sources\ATE\` folder. Most of the abstraction will be based on transferring GBIB commands and data using the **pyvisa** python library.
All of the devices in the setup have a unique address. The pyvisa manager initializes the devices according to the address. Addresses of the devices are stored in the `devices.json` file.
All of the VISA resources inherit from a base class that reads the `devices.json` and initializes the resource according to the tag name associated with the address.
Each device will be loaded using *python resource manager* syntax, for example:

```python
import pyvisa
import ATE  # python/sources/ATE

rm = pyvisa.ResourceManager()  # required, the constructor raises ValueError without it

with ATE.SCU('SCU1', rm) as scu:
    scu.set_voltage(5.5)
```

Examples when more than a single device, initialized in this way (aliases: `ATE.LIA` = `SR860`, `ATE.SCU` = `B2962A`, `ATE.PSU` = `HP6624A`, `ATE.Scope` = `DSO9104A`; the first argument is the tag from `devices.json`):

```python
with ATE.LIA('LIA', rm) as lia, ATE.PSU('PSU', rm) as psu:
    lia.set_offset(845e-3)
    psu.set_voltage(1, 2.9)  # HP6624A: (channel, voltage)
```

> `__exit__` calls `reset()` (`*RST`) on the device before closing the resource, so leaving a `with` block returns the instrument to its default state.

Each ATE device has its own `<device_name>.py` module under the `python/sources/ATE` folder. Each device will expose only the desired functions from the list of functions that will be defined in [a table of functions](#ate-functions-list).
Each `<device_name>.py` will also:

- Implement python `__enter__` and `__exit__` functions for resource manager support.
- Define enum classes according to the [enum lists](#ate-useful-enums).
- A list of helper functions specific for the device.

The project will include `__init__.py` files that will automatically import the devices so that the statement `import GMOS.ATE` will automatically include all of the ATE devices.

#### Status Monitoring Deamons

Some devices will implement a function that can be optionally turned on that will instantiate a daemon thread that will execute commands periodically over GPIB and will raise exceptions if any error occurs. A good example for where this may be useful is for reading the current compliance reached for the ESD protection power supply and stopping the test if the compliance is reached.

#### SR860

> **Implemented in `ATE/sr860.py`:** frequency, phase, amplitude (`SLVL`), offset (`SOFF`), sensitivity, time constant, filter slope, `OUTP?`, `SNAP?`, `APHS`/`ASCL`/`ARNG`, input source/coupling/range. The **`CAPTURE*` commands below are not implemented** (planned for `fft_freq_sweep`).

SR860 supports fully the IEEE488 as well as VXI-11 for streaming data.

| Command | Parameter type | Description |
| ------------- | ------------- | ------------- |
| `FREQ(?) {f}` | Float (Hz/kHz/MHz) | Set/query reference frequency |
| `PHAS(?) {p}` | Float (deg/rad) | Set/query reference phase |
| `SLVL(?) {v}` | Float (V/mV/uV) | Set/query sine output amplitude |
| `SOFF(?) {v}` | Float (V/mV/uV) | Set/query sine output DC level |
| `SCAL(?) {i}` | Integer (Enum) | Set/query sensitivity |
| `OFLT(?) {i}` | Integer (Enum) | Set/query time constant |
| `OFSL(?) {i}` | Integer (Enum) | Set/query filter slope |
| `OUTP? {j}` | Integer (0-15) | Query parameter: 0=X, 1=Y, 2=R, 3=θ |
| `SNAP? {j,k}` | Integers | Query multiple parameters simultaneously |
| `APHS` | None | Execute Auto Phase |
| `ASCL` | None | Execute Auto Scale |
| `ARNG` | None | Execute Auto Range |
| **Capture Buffer** | | |
| `CAPTURECFG(?) { X \| XY \| RT \| XYRT \| i }` | Integer (Enum) | Set/query what is recorded: 0=X only, 1=X and Y, 2=R and θ, 3=X Y R θ. More channels means fewer points per channel for a given buffer size. |
| `CAPTURELEN(?) { n }` | Integer (kB, even, 1–4096) | Set/query capture buffer size in kB. Each float32 sample is 4 bytes. For X-only: `n_points = (n×1024)/4`. Odd values are rounded up to the next even number. |
| `CAPTURERATEMAX?` | — (query only) | Query maximum allowed capture rate in Hz at the current time constant. Depends on time constant and sync filter settings. |
| `CAPTURERATE(?) { n }` | Integer (0–20) | Set capture rate divisor: actual rate = `CAPTURERATEMAX / 2ⁿ`. n=0 gives maximum rate. Query returns the actual rate in Hz, not the divisor n. |
| `CAPTURESTART { ONE \| CONT }, { IMM \| TRIG \| SAMP }` | Two enums (both required) | Start capture. First arg: `ONE`=OneShot (stop when buffer full), `CONT`=Continuous (wrap and overwrite oldest data). Second arg: `IMM`=start immediately, `TRIG`=start or stop on rear-panel TTL falling edge, `SAMP`=one sample per TTL trigger. Always clears any previously captured data. |
| `CAPTURESTOP` | None | Stop capture. Remaining space in the current 2 kB block is zero-filled. Safe to call if capture has already ended. |
| `CAPTURESTAT?` | — (query only) | Query capture state as a 3-bit integer. Bit 0 (weight 1): capture in progress. Bit 1 (weight 2): capture has been triggered. Bit 2 (weight 4): buffer has wrapped. Poll until bit 0 clears to detect completion. |
| `CAPTUREBYTES?` | — (query only) | Query number of valid (non-zero-fill) bytes captured so far. Live during capture. After stop, equals the exact data byte count excluding zero-fill. |
| `CAPTUREGET? { offset_kB }, { length_kB }` | Two integers (both required) | Read `length_kB` kB of capture buffer starting at `offset_kB`. Maximum `length_kB` = 64 per call; loop with increasing offset to read larger buffers. Capture must be stopped first. Returns an IEEE 488.2 definite-length binary block of float32 little-endian values. |

**Sensitivity (`SCAL`)**:
0: 1 V, 1: 500 mV, 2: 200 mV, 3: 100 mV, 4: 50 mV, 5: 20 mV, 6: 10 mV, 7: 5 mV, 8: 2 mV, 9: 1 mV, 10: 500 µV, 11: 200 µV, 12: 100 µV, 13: 50 µV, 14: 20 µV, 15: 10 µV, 16: 5 µV, 17: 2 µV, 18: 1 µV, 19: 500 nV, 20: 200 nV, 21: 100 nV, 22: 50 nV, 23: 20 nV, 24: 10 nV, 25: 5 nV, 26: 2 nV, 27: 1 nV.

**Time Constant (`OFLT`)**:
0: 1 µs up to 21: 30 ks (Follows 1-3-10 sequence).

**Filter Slope (`OFSL`)**:
0: 6 dB/oct, 1: 12 dB/oct, 2: 18 dB/oct, 3: 24 dB/oct.

**Reference Source (`RSRC`)**:
0: Internal, 1: External, 2: Dual, 3: Chopper.

**Input Configuration (`ISRC`)**:
0: A, 1: A-B.

**Input Coupling (`ICPL`)**:
0: AC, 1: DC.

**Input Shield Grounding (`IGND`)**:
0: Float, 1: Ground.

#### Additional Python specifics

- All python code will be **typechecked and linted** using `ruff` and `pyright` packages. All of the rules for linting can be found under the `pyproject.toml` file.
- Preffered package for python directory handling is pathlib. Any inputs from user (for example paths that are received via CLI arguments), are also supported so variables that are associated with user interraction should support in typecheck both **str** and **Path** types.
- Preffered test result file format is `.csv` and the package for the handling of the file is using the python default **csv** package.
- It can be assumed that the project will be always run from its root directory.
- **Logging**: all modules obtain a logger with `logging.getLogger(__name__)`. No module configures the root logger — that is done once in `main.py` via `logging.basicConfig()` with format `%(asctime)s [%(levelname)-8s] %(name)s: %(message)s`. Use `logging.INFO` for normal progress messages and `logging.DEBUG` for VISA command traces. Never use `print()` for diagnostic output.

### `setups\` Implementation Details

The following implementation of tests will be found under the `setups\` directory:

1. **Auxiliary** experiments
    - Linear I-V sweep
    - Logarithmic I-V sweep

All setups are classes that inherit from a setup base-class that include the devices required for the test as well as the measurement parameters. Also, each setup will store its test results under a folder named after the test under the `Results` folder.

#### Linear & Logarithmic I-V Sweep

The purpose of these tests is usually to perform a sanity check for the setup correctness, evaluate an I-V curve of a device or help calibrate setup values for other experiments, thus the actual connectivity of the setup may not be a pre-defined setup connection from the known list stated earlier.
For these two tests, the setup will always use either `SCU1` or `SCU2` from the `devices.json` definition, (this will be decided upon the setup initialization by providing the tag). **Linear sweep** will receive a `start`, `stop` and `step` parameters, while **logarithmic sweep** will receive `start`, `stop` and `step` (applied as arguments to `linspace` or `logspace` functions for **numpy** python library). The general steps for the sweep setup are as follows:

1. Setup of the SCU, including resetting the device, enabling ESD protection.
2. Setting the SCU to either voltage or current mode, and setting the voltage or current compliance (voltage if current mode is set, current if voltage mode is set).
3. Stepping over the voltages according to the sweep parameters as explained earlier for each sweep mode.
4. Storing the results of both the set voltage or current and the actually measured voltage and current. Results will be stored as `.csv` and `.png` files. The title of the `.png` will always be the name of the sweep ("linear sweep" / "logarithmic sweep" is the default name, otherwise received from the user as an argument for the setup). X axis is the forced variable (as set, not as measured) Y is the measured variable.

#### LIA Snap Capture (`lia_snap_only` / `lia_snap_sweep`)

Implemented by `LIAMeasurementSetup` (`python/sources/setups/lia_setup.py`). Configures the LIA + SCU bias from `LIASnapConfig` and captures raw X/Y/R samples at fixed intervals to CSV. `snap_only` captures once at the configured frequency; `snap_sweep` repeats the capture across `frequencies`, writing one CSV per frequency into `sweep_folder` (waiting `first_settle`/`first_auto_phase`/`first_autophase_settle` only on the first point, `settle` on every subsequent one).

#### Gas Response Capture (`lia_gas_response_interactive`)

Implemented by `LIAMeasurementSetup` (`LIAGasResponseInteractiveConfig`): a manually-gated capture for actual gas-dosing runs at a fixed (`temperature`, `lia_frequency`) operating point. After the initial Enter press starts recording, every further Enter press marks the current row as `f"{mark_label_prefix}_N"` without stopping capture, and Esc stops recording — so the operator marks an arbitrary number of gas insertions/removals during the run. Output is one continuous CSV (`gas_response.csv`) with `index`/`event` columns, plus a time-series plot with each mark drawn as a vertical line. `temperature` (a shared heater ch1/ch3 voltage) is applied before `settle`.

#### Post-Processing Setups (`lia_digest_sweep` / `lia_drift_evolution` / `heater_slope_table` / `dwell_analysis`)

All touch no instruments — they operate purely on already-captured CSVs:

- **`heater_slope_table`** (`HeaterSlopeTableConfig`, `python/sources/setups/heater_slope_table.py`) — recomputes heater-sensitivity points and slopes from the MCP monitor CSVs (`monitor_csvs`) instead of live tool readings. Each measurement note (a note containing `R=` and the ch1 readback as `ch1=X` or `pt(X)`) becomes one point: the settled window is the last `window_s` seconds of the dwell since the previous logged setpoint change (`offset ->`, `heater chN ->`, `SCUN voltage ->`), starting no earlier than the last phase auto-zero. The point value is the linear fit of X = R·cos(theta) evaluated at the end of the dwell, with the fit-residual standard error inflated by the lag-1 autocorrelation (`n_eff`). Points are flagged `short_settle`, `over_range`, `phase_suspect` (phase last zeroed at low R), `ch1_mismatch` (note vs logged PSU readback) — excluded from slopes — and `drifting`, `vd_low` (reported only). Slopes are adjacent-ch1 differences within a Vgs visit; the ch1 readback resolution (`heater_resolution_v`, default 1 mV) enters as a uniform quantization error and normally dominates the statistical error. Writes `Results/HeaterSlopeTable/<session>/{points.csv,slopes.csv,slope_table.md}` with N, σ, N_eff and the settle time actually used per point. Monitor logs written before the heater event carried a `(readback X V)` suffix rely on the ch1 value in the operator's note.
- **`dwell_analysis`** (`DwellAnalysisConfig`, `python/sources/setups/dwell_analysis.py`) — quantifies operating-point recalibration needs from isolated-dwell monitor CSVs (`dwell_csvs`): each file must contain one `ISOLATED START` and one `ISOLATED END` note event bracketing a stretch with no instrument calls but the continuous monitor. Fits the linear drift of X = R·cos(theta) over that window (whole-session slope + 30-minute block slopes, `block_s`), and reports the cold-start-to-cold-start shift of X at dwell start across sessions, optionally converted to an equivalent heater-voltage shift via `local_slope_v_per_v` (take this from a `heater_slope_table` slope at the same Vgs/heater point). Writes `Results/DwellAnalysis/<session>/dwell_report.md`.

- **`lia_digest_sweep`** (`LIADigestSweepConfig`, `python/sources/setups/lia_digest_sweep.py`) — digests every raw snap CSV in `sweep_dir` (avg X/Y/R, X/Y RMSE, optional baseline R-drift fit if `baseline=true`) and compiles the digests into R/theta/R-drift-vs-frequency summary plots (`phase_shift_deg` offsets the theta plot only).
- **`lia_drift_evolution`** (`LIADriftEvolutionConfig`, `python/sources/setups/lia_drift_evolution.py`) — analyzes how each frequency point's R-drift rate evolves across a sequentially-captured sweep folder (`digest_dir`), given the wall-clock spacing between captures (`interval_s`).

#### Operating-Point Sweeps (`operating_point_sweep` / `operating_point_offset_sweep`)

Both locate a good DC operating point by sweeping heater voltage (PSU ch1/ch3, i.e. temperature) x LIA DC reference offset and measuring SCU1/SCU2 current; both use `LIAInstrumentConfig` bias fields as the fixed baseline for whichever channel isn't actively being swept:

- **`operating_point_sweep`** (`OperatingPointSweepConfig`, `python/sources/setups/operating_point_sweep.py`) — for every heater-voltage x offset combination, sweeps SCU1 and SCU2 independently through a full `scu_voltages` log-scale IV curve (the other channel held at its configured baseline), producing per-heater-voltage IV plots (offsets overlaid) and a single-offset (`plot_offset_value`) IV plot with heater voltages overlaid.
- **`operating_point_offset_sweep`** (`OperatingPointOffsetSweepConfig`, `python/sources/setups/operating_point_offset_sweep.py`) — a lighter-weight variant: SCU1/SCU2 stay fixed at their configured baseline voltages, and only one current point is measured per heater-voltage x offset combination, producing a current-vs-offset plot per channel with heater voltages overlaid.

#### LIA Offset Sensitivity Sweep (`lia_offset_sensitivity_sweep`)

Measures GMOS current sensitivity to a small heater-voltage (gate temperature) perturbation, at each point of a heater-voltage (PSU ch1/ch3) x SCU-bias (SCU1/SCU2) x LIA-offset sweep, for the active (SCU1, PSU ch1) and blind/reference (SCU2, PSU ch3) devices simultaneously. Unlike the Operating-Point Sweeps, the LIA reference amplitude/frequency are held fixed for the whole run (`amplitude`, `lia_frequency`); only the DC reference offset is swept.

Once the LIA/SCU instruments are configured (bias, sensitivity, filter, compliance) and before the sweep starts, the setup waits `initial_settle` (default 60 s) to let the setup settle from a cold start.

For every `psu_voltages` x `scu_bias_voltages` x `lia_offsets` combination (outer to inner, in that order — both heater channels and both SCU biases set together at each of the outer two levels), each channel is measured independently: `n_measurements` repeated `measure_current()` spot reads are averaged (with their MSE recorded) as the baseline; then only that channel's own PSU heater voltage is bumped by `psu_step` (default 1 mV), held for `step_settle` (default 1 s), and re-averaged as the perturbed reading; the heater voltage is then restored to the nominal `psu_voltages` value before moving to the next point.

Results are written to two separate CSVs per session (`Results/LIAOffsetSensitivitySweep/<session_folder>/active.csv` and `blind.csv`), each with columns `psu_voltage`, `scu_bias_voltage`, `lia_offset`, `baseline_current`, `baseline_mse`, `perturbed_current`, `perturbed_mse`, `psu_step`, `sensitivity_A_per_V`.

#### Differential-Method Calibration (`lia_differential_calibration`)

Finds a heater-voltage (PSU ch1/ch3) operating point for the differential method where the LIA's demodulated X output is both phase-locked (auto-zeroed) and drift-free.

The starting point matches `lia_gas_response_interactive`: heater ch1/ch3 set to `temperature`, LIA reference (offset/amplitude/sensitivity/filter/time constant/input settings) applied from the config, then `initial_settle` (default 60 s) for thermal settling.

Phase auto-zero: `APHS` is issued, the setup waits `phase_zero_wait` (default 5 s), then reads theta; if `abs(theta) > theta_tolerance_deg` (default 0.6°) auto-phase is retried, aborting the whole run after `phase_zero_max_retries` (default 3) failed attempts.

Once phase-locked, X/Y/theta are sampled every `sample_interval` (default 0.5 s) into one continuous CSV for the entire run — sampling never stops, including during settles, auto-phase waits, and PSU steps. Every `window_duration` (default 30 s) the slope of X vs time is fit (recomputed continuously as samples arrive, logged at DEBUG); if `abs(slope)` exceeds `slope_threshold_v_per_s` (default 0.5 µV/s), a bounded coordinate-descent search adjusts the heater voltage: PSU channel 1 is tried first, then channel 3, each in increase-then-decrease order, in `psu_step` (default 5 mV) increments up to `psu_step_max` (default 25 mV) away from `temperature`. Auto-phase is re-run and a new 30 s window measured after every step; a step that improves `abs(slope)` is followed by another step in the same direction, a step that worsens it is reverted before trying the next direction/channel. If no attempt converges within the ±25 mV bounds on either channel, the best configuration found across all attempts is applied as a best-effort result.

Once the operating point is settled (converged or best-effort), a final `final_validation_duration` (default 600 s / 10 min) observation-only window runs at that voltage: X/Y/theta keep being sampled and the slope is fit and logged against `slope_threshold_v_per_s`, but no further PSU adjustment is made — this confirms the chosen point's drift stays low over a longer horizon than the 30 s search windows.

A plaintext `notes` column on the CSV narrates every action taken (heater set, each auto-phase attempt and its theta result, window start/end and computed slope, each PSU step with old→new voltage, improve/revert/exhausted/converged messages); most rows have an empty `notes` cell. A companion time-series plot (X/Y/theta) marks every non-empty note as a vertical line, reusing the same plotting helper as `lia_gas_response_interactive`.

**New files**: `python/sources/setups/differential_calibration.py` — the `DifferentialCalibration` setup class; `DifferentialCalibrationConfig` in `python/sources/config.py`; `python/configs/lia_differential_calibration.example.toml` — example config.

#### Heater Resistance (`heater_resistance`)

Implemented by `HeaterResistance` (`python/sources/setups/heater_resistance.py`, `HeaterResistanceConfig`, example `python/configs/heater_resistance.example.toml`). Needs only the PSU (ESD and fan on): sweeps PSU ch1/ch3 heater voltage, averages `n_samples` readings (`sample_interval` apart) per point, repeats the sweep `n_repeats` times and fits I = V/R. Writes `heater_resistance.csv` and `fit_summary.csv` to `Results/HeaterResistanceSetup/<session>/` and the I-V plot (fit, R², MSE error lines) to `Plots/`.

#### FFT Frequency Response Sweep (`fft_freq_sweep`) — PLANNED, NOT IMPLEMENTED

> **Status:** neither `setups/fft_freq_sweep.py`, its config, nor the SR860 capture-buffer wrapper methods exist yet, and `fft_freq_sweep` is not in `_EXPERIMENTS` in `main.py`. This section is a design specification only.

The goal of this setup is to characterise the **frequency response of the GMOS measurement chain** across a list of LIA reference frequencies and to identify spurs, harmonics, and distortion products in the 300 Hz – 1 kHz band. For each reference frequency the SR860 hardware capture buffer is used to record a time series of the demodulated X output, which is then FFT-analysed entirely in Python. The resulting per-frequency spectrum and peak CSV files are the deliverable, intended for upload to Claude for optimal-frequency selection.

**Parameters** (defined as dataclass fields in the experiment config):

| Parameter | Default | Description |
| --- | --- | --- |
| `freq_list` | `[300, 400, 500, 600, 700, 800, 900, 1000]` Hz | LIA reference frequencies to sweep |
| `capture_rate_n` | `4` | `CAPTURERATE` divisor n; actual rate = `CAPTURERATEMAX / 2⁴` (≈ 4096 Hz at typical time constants). Nyquist comfortably covers the 1 kHz upper band limit. |
| `capture_buflen_kb` | `256` | `CAPTURELEN` in kB. At 4096 Hz, X-only → 65 536 points → 16 s record → ~0.06 Hz frequency resolution. |
| `fft_window` | `hann` | Window function applied before FFT. `hann` for general use; `blackman` for lower sidelobes; `flattop` for best amplitude accuracy on discrete tones. |
| `settle_time_s` | `5.0` | Seconds to wait after writing `FREQ {f}` before starting capture. Must exceed several LIA time constants so the output has stabilised. |
| `f_analysis_start` | `300.0` Hz | Lower bound of the frequency band used for peak search and CSV output. |
| `f_analysis_stop` | `1000.0` Hz | Upper bound of the frequency band used for peak search and CSV output. |
| `results_dir` | `Results/fft_freq_sweep/` | Root output directory. |

**Process overview**:

Configure the capture once before the sweep: write `RSRC 0` (internal reference), `CAPTURECFG X`, `CAPTURELEN {n}`, then set the rate by first querying `CAPTURERATEMAX?` and writing `CAPTURERATE {n}`. Log the actual rate returned by `CAPTURERATE?` — it is needed for all subsequent frequency-axis calculations.

For each frequency in `freq_list`:

1. Write `FREQ {f}` and wait `settle_time_s` for the LIA output to stabilise.
2. Write `CAPTURESTART ONE, IMM` to begin a OneShot capture.
3. Poll `CAPTURESTAT?` in a loop until bit 0 clears (capture complete). Use a timeout of at least `record_time × 1.5 + 5 s` to avoid false timeouts.
4. Write `CAPTURESTOP` and query `CAPTUREBYTES?` to obtain the valid byte count.
5. Read the buffer by looping `CAPTUREGET? {offset}, 64` in 64 kB chunks, incrementing the offset each iteration, until all valid bytes are retrieved. Concatenate the binary payloads.
6. Unpack the payload as float32 little-endian to obtain X(t) in Volts RMS.
7. Compute the FFT: apply the chosen window, run `numpy.fft.rfft`, correct the amplitude for the window's coherent gain and for the single-sided spectrum (double all non-DC, non-Nyquist bins), compute the frequency axis from the actual capture rate and sample count. The result is a calibrated amplitude in V RMS per bin, convertible to dBVrms with `20 × log10(amplitude)`.
8. Find peaks in the `[f_analysis_start, f_analysis_stop]` band and record their frequency, amplitude, and SNR relative to the in-band noise floor (estimated as the median amplitude across the band).
9. Write two CSV files per frequency:
   - `fft_{f}Hz_spectrum.csv` — columns: `freq_hz`, `amplitude_vrms`, `amplitude_dBVrms`
   - `fft_{f}Hz_peaks.csv` — columns: `rank`, `freq_hz`, `amplitude_vrms`, `amplitude_dBVrms`, `SNR_dB`

After all frequencies, write `summary_peaks.csv` with one row per reference frequency containing the noise floor and the top three peaks. This summary file is the primary artifact for Claude upload and optimal-frequency analysis.

**New files required**: `python/sources/ATE/sr860.py` — Existing LIA wrapper methods for the capture buffer commands, the required operators for the capture will be added here as well; `python/sources/setups/fft_freq_sweep.py` — the setup class and FFT/peak logic; `python/configs/fft_freq_sweep.toml` — example config. Add `numpy` to `pyproject.toml` dependencies if not already present.

#### General Notes about the Setup

- ESD protection is always using the PSU channel 2, setting 5 volts and current to 700e-3 amps.
- PSU also controlls setup fan, channel 4 set to 7 volts and 1.5 amps.

## ATE Specifics

In this chapter some additional information regarding the python implementation for the device wrappers will be added, mostly taken from each devices user manual.

### ATE Functions List

**All ATE** equipment supports:

- `*IDN?` - that returns an identification string.
- `*RST` - that resets the device to default.
- `*CLS` - clear all status registers.
- `*STB?` - *Serial Poll Status Byte*, has device specific fields.
- `*OPC?` - returns `1` when all pending operations are completed.

> STB is currently not required to be implemented since it is device specific.

| Device | Command | Parameter type | Description |
| ------------- | :-------------: | :-------------: | :-------------: |
| | | | |
| B2962A | `[:SOUR[c]]:VOLT[:LEV] <v>` | Sets the DC voltage level for channel [c]. | See Source Output Ranges. |
| B2962A | `[:SOUR[c]]:CURR[:LEV] <v>` | Sets the DC current level for channel [c]. | See Source Output Ranges. |
| B2962A | `[:SOUR[c]]:<VOLT/CURR>:MODE` | "Sets source mode to FIXed, LIST, or SWEep." | "FIX, LIST, SWE." |
| B2962A | `:OUTP[c] <state>` | Enables or disables output for channel [c]. | ON (1) or OFF (0). |
| B2962A | `:OUTP[c]:PROT[:STAT]` | Enables Over Voltage/Current protection. | ON (1) or OFF (0). |
| B2962A | `:SENS[c]:FUNC[:ON] <func>` | Enables specific measurement functions. | """VOLT"", ""CURR"", ""RES""." |
| B2962A | `:MEAS?` | Executes a spot measurement and returns data. | None |
| B2962A | `:SENS[c]:<V/I>:APER <time>` | Sets measurement aperture time. | Seconds or MIN/MAX/DEF. |
| B2962A | `:SENS[c]:<V/I>:NPLC <val>` | Sets integration time in Power Line Cycles. | 0.001 to 100. |
| B2962A | `:INIT` | Initiates the trigger system for measurements. | None |
| B2962A | `:ABOR` | Aborts the trigger system and returns to idle. | None |
| B2962A | `:FETC?` | Retrieves data already in the instrument buffer. | None |
| B2962A | `:READ?` | Initiates a measurement and fetches the data. | None |
| B2962A | start_monitor_daemon | channel (enum) | daemon handler (**planned, not implemented in `b2962a.py`**) |
| | | | |
| 6624A | `VSET <ch>, <val>` | ch is 1-4 integer, val is Float (Volts) | Sets the voltage level or limit for channel `<ch>`. |
| 6624A | `ISET <ch>, <val>` | ch is 1-4 integer, val is Float (Amps) | Sets the current level or limit for channel `<ch>`. |
| 6624A | `OUT <ch> <state>` | ch is 1-4 integer, state is 0 or 1 | Enables (1) or disables (0) the specified output. |
| 6624A | `OVSET <ch>, <val>` | ch is 1-4 integer, val is Float (Volts) | Sets the Overvoltage Protection (OVP) trip point. |
| 6624A | `OCP <ch>, <state>` | ch is 1-4 integer, state 0 or 1 | Enables (1) or disables (0) Overcurrent Protection (OCP). |
| 6624A | `OCRST <ch>` | ch is 1-4 integer | Resets an output that was disabled by OCP or OVP. |
| | | | |
| 6624A | `VOUT? <ch>,<ch>`| ch is 1-4 integer | Queries the actual measured output voltage. |
| 6624A | `IOUT? <ch>,<ch>`| ch is 1-4 integer | Queries the actual measured output current. |
| 6624A | `VSET? <ch>,<ch>`| ch is 1-4 integer | Queries the programmed voltage setting. |
| 6624A | `ISET? <ch>,<ch>`| ch is 1-4 integer | Queries the programmed current setting. |
| 6624A | `STS? <ch>,<ch>` | ch is 1-4 integer | Returns the status byte (0–255) for the channel. |
| 6624A | `ERR?` | None | Returns the current programming or hardware error code. |
| | | | |

### Python Wrapper Methods (as implemented in `python/sources/ATE/`)

Audited against the code; update this list whenever a driver changes.

- **`ATEBase`**: `query`, `write`, `read`, `reset`, `clear_status`, `idn`, `opc`; context manager (`__exit__` resets the device). Constructor `(tag, rm)`.
- **`SR860` (LIA)**: `set/get_frequency`, `set/get_phase`, `set/get_amplitude`, `set/get_offset`, `set/get_sensitivity`, `set/get_time_constant`, `set/get_filter_slope`, `get_output(param)`, `snap(*params)`, `auto_phase`, `auto_scale`, `auto_range`, `set_input_source`, `set_input_coupling`, `set/get_input_range`. Enums: `Sensitivity`, `TimeConstant`, `FilterSlope`, `InputSource`, `InputCoupling`, `InputRange`.
- **`B2962A` (SCU1/SCU2)**, all take `channel: int = 1`: `set/get_voltage`, `set/get_current`, `set/get_voltage_compliance`, `set/get_current_compliance`, `set_source_function`, `set_source_mode`, `enable_output`, `disable_output`, `enable_protection`, `disable_protection`, `set_measurement_function`, `measure_spot`, `measure_current`, `set_aperture_time`, `set_nplc`, `initiate_measurement`, `abort_measurement`, `fetch_data`, `read_data`. Enums: `SourceMode`, `SourceFunction`, `MeasurementFunction`.
- **`HP6624A` (PSU)**, channel first: `set_voltage`, `set_current`, `enable_output`, `disable_output`, `set_overvoltage_protection`, `enable_ocp`, `disable_ocp`, `reset_ocp_ovp`, `get_output_voltage`, `get_output_current`, `get_programmed_voltage`, `get_programmed_current`, `get_status`, `get_error`.
- **`DSO9104A` (Scope)**: stub, no functional API.

## ATE Useful Enums

These integer mappings are fixed for the device and should be defined in the wrapper.

### Stanford Research SR860

**Capture Configuration (`CAPTURECFG`)**:
0: X only, 1: X and Y, 2: R and θ, 3: X Y R θ. Use X-only for FFT analysis — one channel maximises the available record length for a given buffer size.

**Capture Rate**:
Always query `CAPTURERATEMAX?` before setting `CAPTURERATE n`, since the maximum rate depends on the current time constant. Setting n=0 gives the maximum; each increment halves it. `CAPTURERATE?` returns the actual rate in Hz, not the divisor. For the 300 Hz–1 kHz analysis band a rate of roughly 4–8 kHz is sufficient (Nyquist > 2× the highest frequency of interest) and keeps the buffer fill time reasonable.

**Buffer size and record time**:
`n_points = (CAPTURELEN_kB × 1024) / (4 × n_channels)` and `record_time_s = n_points / capture_rate_Hz`, giving `freq_resolution_Hz = 1 / record_time_s`. For example: 256 kB buffer, X-only, 4096 Hz → 65 536 points → 16 s record → 0.06 Hz frequency resolution.

**`CAPTUREGET?` binary block format (IEEE 488.2 definite-length)**:
Response bytes: `#nCCCC<payload>` where `#` is a literal hash, `n` is one ASCII digit giving the number of length-digits that follow, `CCCC` is those n ASCII digits giving the payload byte count, and `<payload>` is that many bytes of float32 little-endian data. For multi-channel configurations samples are interleaved: X₀ Y₀ X₁ Y₁ … Since `CAPTUREGET?` is capped at 64 kB per call, the wrapper must loop with increasing offsets and concatenate the raw payloads before unpacking with `numpy.frombuffer(data, dtype="<f4")`.

**What the captured signal is**:
The capture buffer records the **post-filter, demodulated X (and/or Y) output** — the same value returned by `OUTP? 0`, in Volts RMS. This is not the raw BNC input. At the LIA reference frequency the GMOS signal appears as DC in X(t); any noise or interference at f_ref ± Δf appears as a slow oscillation at Δf in X(t). The FFT of X(t) therefore reveals the noise floor and spur structure in the demodulated band, which is the relevant quantity for GMOS frequency-response characterisation.

### Keysight B2962A

These integer or string mappings are fixed for the device and should be defined in the wrapper as constants or Python Enums.

#### Output Configuration

**Source Priority Mode (`:SOUR:RANG:RPR`)**:
NOISe: Low noise priority. TRANsient: Transient speed priority.

**Transient Speed Mode (`:SOUR:TRAN:SPE`)**:
NORMal: Normal speed. FAST: High speed.

**Output Off Mode (`:OUTP:OFF:MODE`)**:
ZERO: Source 0 V or 0 A. HIZ: High impedance. NORMal: Normal output off condition.

**GPIO Pin Function (`:SOUR:DIG:EXT[n]:FUNC`)**:
DIO: Digital I/O, DINPut: Digital Input, HVOL: High Voltage, TINPut: Trigger Input, TOUT: Trigger Output.

#### Data & Measurement

**Data Format (`:FORM[:DATA]`)**:
ASCii: ASCII format. REAL,32: 32-bit floating point. REAL,64: 64-bit floating point.

**Sense Elements (`:FORM:ELEM:SENS`)**:
VOLTage, CURRent, RESistance, TIME, STATus, SOURce.

**Arbitrary Waveform Types (`:ARB:FUNC`)**:
EXP (Exponential), RAMP, SIN (Sinusoidal), SQU (Square), TRAP (Trapezoidal), TRI (Triangle).

