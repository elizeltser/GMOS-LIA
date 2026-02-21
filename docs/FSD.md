# GMOS LIA - Functional Specifications Document
This file is an in-depth full functional specifications documentation document describing the requirements from a hardware setup designed to test and measure the GMOS gas sensor device, mainly for research purpoise.

## Introduction
The GMOS gas sensor is a CMOS-SOI-MEMS device based around the TMOS temperature sensor. The sensor was designed and developed in Technion institude of technology in Israel, by Prof. emeritus Yael Nemirovsky and her research team.
This document is compiled and written by Eli Zeltser - for Msc work and for auto-generation of the code for the setup hardware control.
This document will include:
- Definition of the hardware connectivity for the various experiments and evaluations of the GMOS device.
- Detailed description of the experiments for each hardware connection.
- Definition of the project structure as well as the coding conventions, specific implementation details and code examples.
- Analysis of the results.

> This document will be further written as the repository grows it may not represent its content at any given time.

## Installation & Prerequisits
For the correct usage of this project one must make sure the following programs are installed:
- **Python** version at least 3.13
- **NI-VISA** driver for GPIB devices

To install the project on the PC one run the following commands:
```shell
python -m venv .venv
.\.venv\Scripts\activate
# for Linux or MAC that will be source ./.venv/Scripts/activate
git clone https://github.com/elizeltser/GMOS-LIA.git
cd GMOS-LIA
pip install .
```

## List of Acronyms
| Acronym  | Meaning |
| ------------- |:-------------:|
| GMOS | Gas MOS |
| LIA  | Lock in amplifier     |

# Hardware Connectivity
The hardware setup for the GMOS experimentation is one of the following:
1. Single ended connection
2. Bridge connection

In addition to the above experiment use-cases, there are several additional usefull setups that are usefull for general usage and setup debugging:
1. I-V sweep

## Definitions for the GMOS
Each DUT chip contains 6 GMOS devices, two of which have slightly different heat properties thus they are never used. The remaining four devices are divided for **active and blind** pairs. A bridge connection always tests pairs of active-blind, while single ended connection measures only one device at a tile. The DUT chip exposes all of the pins for each GMOS device as well as dedicated pins for GND and VDD, which must be powered with 5v between them whenever the DUT is used (essential for ESD protection and proper operation). Apart from the unrelated pins mentioned previously, the DUT chip has the following list of pins **for each GMOS device** (i.e multiplied by 6):
- GMOS drain
- GMOS source
- GMOS gate
- Heater positive
- Heater negative

There are two ways to connect the GMOS:
- **2T method** where GMOS drain is connected to its gate
- **3T method** where GMOS gate and drain are not necesseraly the same.
 
## Automatic Test Equipment
The hardware components of the setup for the GMOS analysis are high-end test and measurement devices, here is a full list of the devices that are all connected in the setup:
- SR860 Lock in amplifier
- Keysight b2962a source and measurement
- HP 6624 power supply
- HP 8116A Signal generator
- Keysight DSO9104A Infiniium scope

All of the devices GPIB or IP addresses are stored in the `devices.json`.
Here is a table with additional information:
| Device  | Tag | Address| IDN string | 
| ------------- |:-------------:|:-------------:|-------------|
| **SR860** | LIA | `TCPIP::132.68.54.194::INSTR` | "Stanford_Research_Systems,SR860,003693,V1.51\n" |
| **Keysight DSO9104A** | Scope | `TCPIP::132.68.54.234::INSTR` | "KEYSIGHT TECHNOLOGIES,DSO9104A,MY53130118,06.00.00901\n" |
| **Keysight B2962A** | SCU1 | `GPIB0::22::INSTR` | "Keysight Technologies,B2962A,MY52350661,2.2.1744.8725\n" |
| **Keysight B2962A** | SCU2 | `GPIB0::23::INSTR` | "Keysight Technologies,B2962A,MY52350537,2.0.1613.9020\n" |
| **HP 6624a** | PSU | `GPIB0::14::INSTR` | "\n" | 
| **HP 8116a** | SG | `GPIB0::16::INSTR` | "\n" |

> Not all of the equipment is used for all the setup scenarios.

## Single ended connection
In this connection, the GMOS device is connected in **2T configuration**, its gate (and drain) are connected to a resistor whose other port is connected to the reference output of the `SR860`. the drain of the GMOS is connected to the `SR860` input in single ended mode. The heater positive line is connected to the signal output port of the `8116A`.

## Bridge connection
In the bridge connection, two GMOS devices are connected exactly in the **same way they are connected in the single ended connection**, with slight differernces. First, because now there are two signals that can be measured using the LIA, its input here is configured to be differential.

# Project Structure
The automation work included in this repository should be written in **Python**. This will make the tests and scripts that control the setup easier to write. The python program will have two possible entry points, either **regular python scripting**, or **pytest** that can be very useful with its fixtures and parametrization of tests. Project may require additional hardware components such as MCUs or FPGAs.
> While *currently* not in use, we may require generatig low-level communication signals. The code of those components will be stored in their own separate folder from the project to help organize the files.

```
- / Project root
|
--- /.venv
--- /python
---     / sources # ATE control
---         ATE/ # wrappers for GPIB devics
---         setups/ # definition of experiment scenarios
---     / testing # TBD - i.e testing the ATE control via mocks
---     main.py
--- / Firmware
---     / **TBD**
--- / Experiments
---     / use-cases # python experiments entry points
---     / parametrized-tests # another pytest entry point
--- / Results # *TODO: explain the organization here*
--- devices.json
--- pyproject.toml
--- .gitignore
```

## Python Modules
Since we do not desire to utilize the low level operational commands directly, we will create python wrapperes that abstracts away the existing ATE APIs (mostly GPIB commands and streaming data in special cases such as for the LIA and the scope).  
Additionaly under the `python\setups\` directory, the actual implementation of the experiment will reside.
The **main entry point for the project** (i.e `main.py`) will implement a CLI that will receive the name of the experiment as an argument and will implement the experiment. For example when executing:

```shell
python -m GMOS --IV-voltage-lin
# Executes linear Voltage force, current measure sweep, with start, stop, step triplet hard-coded in setup init.
python -m GMOS --SG-pulse-burst
# Here all of the configurations is hardcoded in the setup init.
```

> pytest entry point TBD...

### `ATE` Implementation Details
ATE device wrappers will be written in the `python\ATE\` folder. Most of the abstraction will be based on transferring GBIB commands and data using the **pyvisa** python library.
All of the devices in the setup have a unique address. The pyvisa manager initializes the devices according to the address. Addresses of the devices are stored in the `devices.json` file.
All of the VISA resources inherit from a base class that reads the `devices.json` and initializes the resource according to the tag name associated with the address.
Each device will be loaded using *python resource manager* syntax, for example:
```python
import GMOS.ATE as ATE
import pyvisa

visa_manager = pyvisa.ResourceManager()

with ATE.PSU('SCU1') as psu:
    psu.set_voltage(5.5)
```

Examples when more than a single device, initialized in this way:
```python
import GMOS.ATE as ATE
import pyvisa

visa_manager = pyvisa.ResourceManager()

with ATE.PSU('SCU1'), ATE.LIA() as psu, lia:
    lis.set_offset(845e-3)
    psu.set_voltage(5.5)
```

Each ATE device will have its own `<device_name>.py` module under `python/sources/devices` folder. Each device will expose only the desired functions from the list of functions that will be defined in [a table of functions](#ate-functions-list).
Each `<device_name>.py` will also:
- Implement python `__enter__` and `__exit__` functions for resource manager support. 
- Define enum classes according to the [enum lists](#ate-usefull-enums).
- A list of helper functions specific for the device.

#### Status Monitoring Deamons
Some devices will implement a function that can be optionally turned on that will instantiate a deamon thread that will execute commands periodically over GPIB and will raise exceptions if any error occures. A good example for where this may be usefull is for reading the current compliance reached for the ESD protection power supply and stopping the test if the compliance is reached.

#### SR860
SR860 supports fully the IEEE488 as well as VXI-11 for streaming data. 
| Command | Paramet type | Description |
|-------------|-------------|-------------|
| `FREQ(?) {f}`       | Float (Hz/kHz/MHz)  | Set/query reference frequency |
| `PHAS(?) {p}`       | Float (deg/rad)     | Set/query reference phase |
| `SLVL(?) {v}`       | Float (V/mV/uV)     | Set/query sine output amplitude |
| `SOFF(?) {v}`       | Float (V/mV/uV)     | Set/query sine output DC level |
| `SCAL(?) {i}`       | Integer (Enum) | Set/query sensitivity |
| `OFLT(?) {i}`       | Integer (Enum) | Set/query time constant |
| `OFSL(?) {i}`       | Integer (Enum) | Set/query filter slope |
| `OUTP? {j}`   | Integer (0-15) | Query parameter: 0=X, 1=Y, 2=R, 3=θ |
| `SNAP? {j,k}` | Integers | Query multiple parameters simultaneously |
| `APHS` | None | Execute Auto Phase |
| `ASCL` | None | Execute Auto Scale |
| `ARNG` | None | Execute Auto Range |

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

### `setups\` Implementation Details
The following implementation of tests will be found under the `setups\` directory:
- **Single ended 2T** experiments:
    - Signal generated pulse burst
- **Auxiliury** experiments
    - Linear I-V sweep
    - Logorithmic I-V sweep

All setups are classes that inherit from a setup base-class that include the devices required for the test as well as the measurement paremeters. Also, each setup will store its test results under a folder named after the test under the `Results` folder.

#### Linear & Logorithmic I-V Sweep
The purpoise of these tests is usually to perform a sanity check for the setup correctness, evaluate an I-V curve of a device or help calibrate setup values for other experiments, thus the actual connectivity of the setup may not be a pre-defined setup connection from the known list stated earlier.
For these two tests, the setup will always use either `SCU1` or `SCU2` from the `devices.json` definition, (this will be decided upon the setup initialization by providing the tag). **Linear sweep** will receive a `start`, `stop` and `step` parameters, while **logorithmic sweep** will receive `start`, `stop` and `step` (applied as arguments to `linspace` or `logspace` functions for **numpy** python library). The general steps for the sweep setup are as follows:
1. Setup of the SCU, including resetting the device, enabling ESD protection (usually the PSU).
2. Setting the SCU to either voltage or current mode, and setting the voltage or current compliance (voltage if current mode is set, current if voltage mode is set).
3. Stepping over the voltages according to the sweep parameters as explained earlier for each sweep mode.
4. Storing the results of both the set voltage or current and the actualy measured voltage and current. Results will be stored as `.csv` and `.png` files. The title of the `.png` will always be the name of the sweep ("linear sweep" / "log sweep" is the default name, otherwise received from the user as an argument for the setup). X axis is the forced variable (as set, not as measured) Y is the measured variable.

#### Signal Generated Pulse Burst
This purpoise of this setup is to evaluate the temperature dependence of a single GMOS as measured using the LIA when applying constant current to the GMOS drain port. The available parameters which may effect the experiment are the **LIAs amplitude, frequency and offset**, as well as the **signal generators pulse width and amplitude**. For a selected list of parameters listed above, the experiment will execute as follows:
1. Setup of the ATEs, including resetting the devices, enabling ESD protection (usually the PSU).
2. Setting the LIA parameters.
3. Preporation of the signal generated pulse (but not triggering yet).
4. Enabling the stream of X and Y data from the LIA to the computer and initializign a deamon to capture the output to a `.csv` file containing sample data with respect to the time.
5. Triggering the pulse of the signal generator
6. waiting for `500ms` (*TODO: wait for scope trigger when we add the scope data*).
7. Stop stream of data to the `.csv` and store it to the `Results` folder.

# ATE Specifics
In this chapter some additional information regarding the python implementation for the device wrappers will be added, mostly taken from each devices user manual.

## ATE Functions List

**All ATE** equipment supports:
- `*IDN?` - that returns an identification string.
- `*RST` - that resets the device to default.
- `*CLS` - clear all status registers.
- `*STB?` - *Serial Poll Status Byte*, has device specific fields.
- `*OPC?` - returns `1` when all pending operations are completed.

> STB is currently not implemented since it is specific for each device

| Device  | Command | Paramet type | Description |
| ------------- |:-------------:|:-------------:|:-------------:|
|||||
| B2962A | `[:SOUR[c]]:VOLT[:LEV] <v>`  | Sets the DC voltage level for channel [c]. | See Source Output Ranges. |
| B2962A | `[:SOUR[c]]:CURR[:LEV] <v>`  | Sets the DC current level for channel [c]. | See Source Output Ranges. |
| B2962A | `[:SOUR[c]]:<VOLT/CURR>:MODE` | "Sets source mode to FIXed, LIST, or SWEep." | "FIX, LIST, SWE." |
| B2962A | `:OUTP[c] <state>` | Enables or disables output for channel [c]. | ON (1) or OFF (0). |
| B2962A | `:OUTP[c]:PROT[:STAT]` | Enables Over Voltage/Current protection. | ON (1) or OFF (0). |
| B2962A | `:SENS[c]:FUNC[:ON] <func>` | Enables specific measurement functions. | """VOLT"", ""CURR"", ""RES""." |
| B2962A | `:MEAS?` | Executes a spot measurement and returns data. | None  |
| B2962A | `:SENS[c]:<V/I>:APER <time>` | Sets measurement aperture time. | Seconds or MIN/MAX/DEF. |
| B2962A | `:SENS[c]:<V/I>:NPLC <val>` | Sets integration time in Power Line Cycles. | 0.001 to 100. |
| B2962A | `:INIT` | Initiates the trigger system for measurements. | None |
| B2962A | `:ABOR` | Aborts the trigger system and returns to idle. | None |
| B2962A | `:FETC?` | Retrieves data already in the instrument buffer. | None |
| B2962A | `:READ?` | Initiates a measurement and fetches the data. | None |
| B2962A  | start_monitor_deamon       | chanel (enum) | deamon handler |
|||||
| 6624A | `VSET <ch>, <val>` | ch is 1-4 integer, val is Float (Volts) | Sets the voltage level or limit for channel <ch>. |
| 6624A | `ISET <ch>, <val>` | ch is 1-4 integer, val is Float (Amps) | Sets the current level or limit for channel <ch>. |
| 6624A | `OUT <ch> <state>` | ch is 1-4 integer, state is 0 or 1 | Enables (1) or disables (0) the specified output. |
| 6624A | `OVSET <ch>, <val>` | ch is 1-4 integer, val is Float (Volts) | Sets the Overvoltage Protection (OVP) trip point. |
| 6624A | `OCP <ch>, <state>` | ch is 1-4 integer, state 0 or 1 |Enables (1) or disables (0) Overcurrent Protection (OCP). |
| 6624A | `OCRST <ch>` | ch is 1-4 integer |Resets an output that was disabled by OCP or OVP. |

| 6624A | `VOUT? <ch>,<ch>`| ch is 1-4 integer | Queries the actual measured output voltage. |
| 6624A | `IOUT? <ch>,<ch>`| ch is 1-4 integer | Queries the actual measured output current. |
| 6624A | `VSET? <ch>,<ch>`| ch is 1-4 integer | Queries the programmed voltage setting. |
| 6624A | `ISET? <ch>,<ch>`| ch is 1-4 integer | Queries the programmed current setting. |
| 6624A | `STS? <ch>,<ch>` | ch is 1-4 integer | Returns the status byte (0–255) for the channel. |
| 6624A | `ERR?` | None | Returns the current programming or hardware error code. |
|||||
| 8116A | `FRQ` | Set the frequency,"HZ, KZ, MZ",1 mHz to 50 MHz | None |
| 8116A | `AMP` | Set the amplitude,"V, MV",10 mV to 16.0 Vpp (50Ω) | None |
| 8116A | `OFS` | Set the DC Offset,"V, MV",0.00 to ±7.95 V | None |
| 8116A | `WID` | Set the pulse Width,"NS, US, MS",10 ns to 999 ms | None |
| 8116A | `DTY` | Set the duty Cycle,%,10% to 90% | None |
| 8116A | `BUR` | Set the burst Count,#,1 to 1999 cycles (Opt 001) | None |
| 8116A | `SWT` | Set the sweep Time,"S, MS",10 ms to 500 s per decade | None |
| 8116A | `STA` | Set the sweep Start,"HZ, KZ, MZ",Start frequency for sweep | None |
| 8116A | `STP` | Set the sweep Stop,"HZ, KZ, MZ",Stop frequency for sweep | None |

## ATE Usefull Enums
These integer mappings are fixed for the device and should be defined in the wrapper.
### Stanford Research SR860


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
### HP 8116A
The HP 8116A uses specific character codes to select modes and waveforms. These should be defined as constants in your wrapper.

| Category | Mnemonic | Value Description |
| ------------- |:-------------:|:-------------:|
| Waveform (W) | W1 | Sine Wave | 
|  | W2 | Triangle Wave | 
|  | W3 | Square Wave | 
|  | W4 | Pulse | 
|  | W0 | DC Only | 
| Operating Mode (M) | M1 | Normal (Continuous) | 
| | M2 | Triggered | 
| | M3 | Gate | 
| | M4 | External Width | 
| | M5 | Internal Sweep (Opt 001) | 
| | M6 | External Sweep (Opt 001) | 
| | M7 | Internal Burst (Opt 001) | 
| | M8 | External Burst (Opt 001) | 
| Control Mode (C) | C0 | Off (Normal) | 
| | C1 | FM (Frequency Modulation) | 
| | C2 | AM (Amplitude Modulation) | 
| | C3 | PWM (Pulse Width Modulation) | 
| | C4 | VCO (Voltage Controlled Oscillator) | 
| Trigger Slope (T) | T0 | Off | 
| | T1 | Positive Edge | 
| | T2 | Negative Edge | 