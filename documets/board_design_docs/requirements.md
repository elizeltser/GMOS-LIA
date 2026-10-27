# GMOS LIA Board — Requirements

This file is the single source for requirement IDs and target values. Design chapters ([schematic_overview.md](schematic_overview.md)) describe how each requirement is met; theory is in [measurement_principles.md](measurement_principles.md); firmware implementation in [firmware.md](firmware.md); verification in [simulations.md](simulations.md) and [preliminary_lab_test_results.md](preliminary_lab_test_results.md).

Requirements are written to be **implementation-neutral** where a design decision is still open; the open decision is named (e.g. D-18) and the candidate implementations are in schematic_overview.md.

**Change log**

| Rev | Date | Changes |
|-----|------|---------|
| A | 2026-09 | Initial set (2 channels, analog oscillator, STM32G474) |
| B | 2026-10-20 | MCU-generated programmable excitation, STM32U575, USB-C PD, +5VP, DG-7…DG-9 |
| C | 2026-10-21 | One active/blind pair operated at a time, others disconnected (active 1–3, blind 4–6) |
| D | 2026-10-22 | Split gate, AD630 gain ±2 |
| E | 2026-10-28 | `CHANGED`: front-end requirements made implementation-neutral, pending D-18 (AN-19…AN-26, new AN-23b); R_D one per side on the board side, readout at the R_D node, TMUX1104 removed (AN-8, AN-11, AN-28, AN-29); coarse/fine drain bias (AN-10); calibration by precision dummy loads (AN-29e); lab input (DC-1); V_REF (DC-4d); isolated UART via external cable (DG-4); SWD header (DG-5); new firmware chapter R.4 (FW-1…FW-16) |

---

## R.1 DC (Power)

| ID | Parameter | Value |
|----|-----------|-------|
| DC-1 | Input | USB-C PD sink, fixed 12 V PDO (15 V acceptable); operating input range 11–15 V. Converters must not start on a 5 V-only source. Second input: lab supply on a terminal block (J4), OR-ed by Schottky diodes; neither input may back-feed the other |
| DC-2 | Intermediate rails | +7 V buck. −7 V inverting buck-boost **only if D-18 = FE-A or FE-B** |
| DC-3 | Max ripple on intermediate rails | 10 % of rail voltage (design achieves < 0.2 %) |
| DC-4 | Analog rails | +5VA (linear). −5VA (linear) **only if D-18 = FE-A or FE-B** |
| DC-4a | Rail-reversal protection | Schottky diode +5VA → GND; GND → −5VA if −5VA exists |
| DC-4b | Heater rail | +5VP, linear regulated, separate from +5VA |
| DC-4c | MCU analog supply | VDDA = 3.3 V, low noise; it is the MCU DAC/ADC reference (LQFP64 has no VREFBUF). Decision D-D: ferrite-filtered +3V3_D with firmware amplitude calibration, or a precision 3.3 V reference (≤ 10 ppm/°C, ≥ 5 mA) |
| DC-4d | Signal reference (FE-C only) | V_REF = 2.5 V, ≤ 30 ppm/°C, low output impedance, star-routed; feeds in-amp REF, band-pass returns, demodulator zero input, post-filter, ADC reference inputs |
| DC-4e | In-amp negative bias (FE-C only) | ≈ −0.23 V, ≥ 5 mA (in-amp V− only) |
| DC-5 | Digital rail | +3V3_D (linear regulated) |
| DC-6 | Load current per rail | See [§6](schematic_overview.md#6-power-budget) (values with 1.5× margin) |
| DC-7 | Converter switching mode | Forced PWM (fixed frequency) at all loads, so no burst frequencies fall in the 377–711 Hz signal band |

---

## R.2 Analog

### R.2.1 Excitation (Gate)

| ID | Parameter | Value |
|----|-----------|-------|
| AN-1 | Excitation frequency | Programmable, default 518 Hz; usable range set by the band-pass (≈ 400–700 Hz); resolution ≤ 0.5 Hz; accuracy and stability follow the MCU clock (DG-7, ±20 ppm). Implementation: FW-1…FW-4 |
| AN-2 | Excitation source and references | One sine from MCU DAC1_OUT1 (timer-triggered DMA table, N = 128 samples/period), filtered by the gate stages. In-phase (X) and quadrature (Y) references are logic square waves from a second timer, 90° apart, phase-coherent with the sine by an exact integer clock ratio ([§2.12](measurement_principles.md#212-excitation-and-reference-generation)) |
| AN-3 | Gate voltage | Two gate nets: `GATE_A` (pixels 1–3) and `GATE_B` (pixels 4–6). Each driven by its own MFB low-pass summing stage: the **same** excitation sine plus its own DC (AN-5). The two AC paths match within 0.2 % / 0.1° (0.1 % R, 1 % C0G) |
| AN-4 | Gate AC amplitude | Programmable 0.5–20 mVpp, default 5 mVpp, set by table scaling; fixed analog attenuation 1/120 |
| AN-5 | Gate DC range / resolution | 0.97–1.2 V, ≤ 100 µV resolution, per gate net. Two DAC80508 channels (16-bit, 38 µV LSB), DC gain ≈ 1.008 through the MFB stage; offset calibrated |
| AN-6 | Reference levels | Logic 0/3.3 V square waves from MCU timer outputs, 100 Ω series. Receiving input per D-18: AD630 comparator (SEL B, SEL A at a mid-level) or analog-switch select input (V_IH ≤ 1.5 V) |
| AN-7 | Excitation stability | Frequency ±50 ppm (clock-derived). Amplitude stability ≤ 100 ppm/°C, set by VDDA (DC-4c) and the MFB resistors (0.1 %, ≤ 25 ppm/°C) |
| AN-7a | Monitoring | Reference timing is known by construction; the gate signal and the references are brought to test points for scope verification (LAB-4) |
| AN-7b | Excitation distortion | THD ≤ 0.3 % at the gate at 5 mVpp; DAC image (≈ 66 kHz) ≤ −40 dBc at the gate (SIM-19) |

### R.2.2 Drain Bias

| ID | Parameter | Value |
|----|-----------|-------|
| AN-8 | Topology | Per side (active, blind): drain-supply amplifier → R_D = 330 kΩ (0.1 %, ≤ 25 ppm/°C thin film, matched pair from one reel) → TMUX1109 bank A → selected drain. R_D is on the board side of the switch, one per side |
| AN-9 | Voltage range | 0.5–3.5 V at the supply side of R_D |
| AN-10 | Voltage resolution | ≤ 100 µV required; coarse/fine difference amplifier from two DAC80508 channels per side, k = R_F/R_G = 0.1 → ≈ 84 µV coarse, 3.8 µV fine over a 250 mV trim ([§2.14](measurement_principles.md#214-drain-bias-with-coarse-and-fine-dacs)). Supply noise at the drain node ≤ 50 nV/√Hz at f₀ (output RC filter 1 kΩ + 10 µF) |
| AN-11 | Current measurement | Each side's drain node (R_D/switch node, same node as the in-amp input): high-Z buffer with gain 8 → RC (≈ 16 Hz) → MCU ADC1 (14-bit). ≈ 25 µV/LSB at the drain → ≈ 76 pA/LSB; I_D = (V_supply − V_D)/R_D. Nothing else (in particular no current-sense amplifier) connects to the drain node |
| AN-12 | Drain outputs | 2 supply channels (active side, blind side), applied through TMUX1109 bank A; unselected pixels have their drain open |
| AN-12a | Drain operating point | I_D 5–10 µA → drain node 50–250 mV DC. With heaters on, firmware keeps V_DS above 3·k_B·T/q at pixel temperature plus half the AC swing ([§2.4](measurement_principles.md#24-transistor-operating-point)) |
| AN-12b | Drain DC mismatch (active − blind) | ≤ ±200 mV (in-amp DC headroom at G = 10). Firmware nulls it with the drain-supply DACs |

### R.2.3 Heaters

| ID | Parameter | Value |
|----|-----------|-------|
| AN-13 | Topology | DAC + op-amp driver per side (switched to the selected pixel by TMUX1109 bank B), DC voltage; feedback taken at the heater side of the current shunt (Kelvin) |
| AN-14 | Voltage range | 2.5–4.0 V |
| AN-15 | DAC resolution | 16-bit |
| AN-16 | Heater resistance | 600 Ω–1.2 kΩ → 2.1–6.7 mA. `ASSUMPTION`, conflicts with "≈ 300 Ω nominal" in the experiment notes (README §9.2 item 2) |
| AN-17 | Heater outputs | 2 channels (active side, blind side), switched to the selected pixels; heaters of unselected pixels are open (off) |
| AN-18 | Current measurement accuracy | ≤ 100 µA. INA190A1 (G = 25) + shunt ≤ 100 mV drop at maximum current (15 Ω for ≤ 6.7 mA); INA190 supplied from VDDA |

### R.2.4 Amplification & Filtering

| ID | Parameter | Value |
|----|-----------|-------|
| AN-19 | Topology | DC-coupled instrumentation amplifier (CMOS/FET input) → 2nd-order Sallen-Key HPF → 2nd-order Sallen-Key LPF → synchronous demodulator (AN-24) → first-order post-filter (AN-26). Implementation per decision **D-18** (FE-A / FE-B / FE-C, [schematic_overview §4.9](schematic_overview.md#49-front-end-architecture-options-decision-d-18)) |
| AN-20 | Gain | In-amp G = 10 (limited by AN-12b). Gain before the demodulator ≥ 20 (target 40). Overall scale factor at the ADC: \|V_X − V_ref\| = 38.2·v̂_diff·cos θ ± 1 % after calibration ([§2.9](measurement_principles.md#29-gain-distribution-headroom-and-demodulator-output)) |
| AN-21 | Bandwidth | f₀ = 518 Hz, −3 dB band 377–711 Hz (section Q = 1) |
| AN-22 | Filter slopes | 40 dB/decade on each side |
| AN-23 | Noise / CMRR | Sensor-limited: amplifier and ADC contribute ≤ 10 % of the total noise power at the ADC (in-amp ≤ 50 nV/√Hz input-referred against ≈ 730 nV/√Hz differential shot noise). In-amp CMRR ≥ 100 dB at G = 10, DC–60 Hz. System CMRR ≥ 48 dB (median, SIM-12) |
| AN-23a | Linear input range | Differential drain signal ≥ 50 mV pk before any stage or the ADC clips; the ADC must clip first |
| AN-23b | Baseline drift | Post-demodulator offset drift ≤ 0.2 µV/°C referred to the differential drain signal (SIM-17) |

### R.2.5 Demodulation (Lock-in)

| ID | Parameter | Value |
|----|-----------|-------|
| AN-24 | Demodulator | Synchronous (multiplying by ±1), X and Y channels, square-wave references from the MCU (AN-2, AN-6). Implementation per D-18: AD630 pair (FE-A) or analog switch + op-amp (FE-B, FE-C) |
| AN-25 | Demodulator gain / accuracy | Per D-18 (AD630 ±2, switch ±1). After calibration: gain error ≤ 0.5 %, X/Y orthogonality ≤ 0.2°, linearity ≤ 0.1 % from 10 mV to full scale (SIM-10, SIM-11) |
| AN-26 | Post-demodulation filter | τ = 500 ms (first order, f_c = 0.318 Hz), inverting, output centred on the ADC reference (VMID or V_REF); ADC measures X − ref and Y − ref differentially. Longer time constants in software |

### R.2.6 Channel Selection

| ID | Parameter | Value |
|----|-----------|-------|
| AN-27 | Channels | 6 pixels: active 1–3, blind 4–6. One pair (one active + one blind, any combination) operated at a time; the others disconnected. Plus one calibration position |
| AN-28 | Selection | Per side one TMUX1109 dual 4:1 (bank A: drain path between R_D and the pixel drain; bank B: heater). The two sides are addressed independently (A0/A1 each), common enable with pull-down (all off at reset) |
| AN-29 | Switched signals | Per pixel: drain and heater, switched together. Gates are not switched (two group nets) |
| AN-29a | Switched signal level | Drain: 50–250 mV DC + up to ≈ 400 mVpp at f₀. Heater: 0–4.0 V DC, ≤ 6.7 mA (≤ 13.3 mA if 300 Ω heaters are confirmed) |
| AN-29b | Switch on-resistance | ≤ 5 Ω (heater path); drain path uncritical in series with 330 kΩ |
| AN-29c | Switch leakage | ≤ 100 pA typ. at 25 °C (≤ 33 µV DC error at the drain node) |
| AN-29d | Other switch parameters | 0–4.5 V signals on single +5VA, ≥ 15 mA continuous per channel, 1.8/3.3 V logic, break-before-make, same part both sides (matched capacitance) |
| AN-29e | Calibration loads | Position 4 of bank A: R_CAL ≈ 18 kΩ 0.1 % to GND per side (pixel-like operating point, [§2.13](measurement_principles.md#213-calibration)). Position 4 of bank B: dummy heater 680 Ω–1 kΩ 0.1 % per side. Optional: active-side R_CAL returned through 100 Ω driven from DAC1_OUT2 via 10 kΩ for a gain/phase test tone |

### R.2.7 Data Converters

| ID | Parameter | Value |
|----|-----------|-------|
| AN-30 | X/Y ADC | 24-bit ΔΣ (ADS1220), 2 differential inputs, SPI, 20–1000 SPS, ±2.048 V full scale (internal reference); noise ≈ 3.9 µV rms at 20 SPS, gain 1 |
| AN-31 | Heater current ADC | MCU ADC (12/14-bit), 2 channels, must meet AN-18 |
| AN-32 | Drain current ADC | MCU ADC1 (14-bit) with ×8 front end, must meet AN-11 |

### R.2.8 Miscellaneous

| ID | Parameter | Value |
|----|-----------|-------|
| AN-33 | GMOS package ESD protection | Supplied from +5VA, ≈ 5 mA |
| AN-34 | Test points | BPF output, reference ground (VMID/V_REF), both gate nets, X/Y references, EXC_DAC: accessible for scope and for an external SR860 as a fallback demodulator |

---

## R.3 Digital (Hardware)

| ID | Requirement |
|----|-------------|
| DG-1 | MCU STM32U575RGT6 (LQFP64) controlling all DACs, ADCs, pixel selection and excitation |
| DG-2 | Digital temperature sensor: COTS, readily available, open-source drivers |
| DG-3 | Digital humidity sensor: same criteria as DG-2 |
| DG-4 | Serial link to PC: UART through a 2-channel digital isolator (ISO6721) to a 6-pin header in FTDI TTL-232R pin order (GND, CTS, VCC, TXD, RXD, RTS); the isolated side is powered from the cable; no board-ground pin on that header. Command/response plus streamed samples ([§5.6](schematic_overview.md#56-pc-link)) |
| DG-5 | SWD header with SWDIO, SWCLK, NRST, VDD, GND (33 Ω series on SWDIO/SWCLK) |
| DG-6 | MCU internal ADC1 (14-bit) for drain sense and heater currents |
| DG-7 | MCU clock from an external 16 MHz CMOS oscillator (XO), ±20 ppm, HSE bypass. Not a bare crystal |
| DG-8 | MCU DAC1_OUT1 (PA4) = gate excitation. DAC1_OUT2 (PA5) = optional calibration tone. Both reserved |
| DG-9 | USB-C PD controller configurable from the MCU over I²C (PDO selection, status) |
| DG-10 | Two timer outputs for the X and Y references on pins of one timer with ≥ 2 output-compare channels (proposal TIM8 CH1/CH2 on PC6/PC7; confirm in CubeMX, [firmware.md §F.2](firmware.md#f2-cubemx-configuration)) |

---

## R.4 Firmware

Detailed design, CubeMX settings and code structure: [firmware.md](firmware.md). Code is generated from an STM32CubeMX project (STM32CubeU5 HAL) and extended in user code sections.

### R.4.1 Excitation and References

| ID | Requirement |
|----|-------------|
| FW-1 | Generate the gate excitation as a sine on DAC1 CH1 (PA4) from an N = 128-entry table, one sample per hardware trigger from a sample timer, via GPDMA in circular (linked-list) mode, without CPU involvement during operation |
| FW-2 | Generate the X and Y references as 50 % square waves on two output-compare channels of one reference timer (toggle mode), X in phase with table sample 0, Y delayed by exactly N/4 samples (90°) |
| FW-3 | Sample timer and reference timer run from the same kernel clock with (ARR_r + 1)(PSC_r + 1) = (N/2)(ARR_s + 1) exactly, and are started by one hardware trigger (master/slave), so sine and references are phase-locked with zero drift |
| FW-4 | Frequency programmable 305–700 Hz (default 518 Hz); the firmware computes ARR_s = round(f_TIM/(N·f₀)) − 1 and reports the actual frequency f_TIM/(N·(ARR_s + 1)) |
| FW-5 | Amplitude programmable 0.5–20 mVpp at the gate (gate = DAC amplitude / 120); the table is recomputed in a second buffer and swapped at a period boundary, or written while the excitation is stopped |
| FW-6 | Phase offset of the references relative to the sine programmable in steps of 360°/N by rotating the table start index |
| FW-7 | Start/stop sequence: excitation starts only after rails, VDDA and the gate DC levels are set; stop leaves the DAC at mid-scale (gate at its DC level) and the references low |
| FW-8 | Changing frequency stops both timers and the DMA, reconfigures, and restarts them synchronously; X/Y samples taken within 7τ (3.5 s) after a change are flagged invalid |
| FW-9 | Optional calibration tone on DAC1 CH2 (PA5): same trigger and table length as CH1, independent amplitude, on/off |
| FW-10 | A UART command interface sets and reads frequency, amplitude, phase index, run/stop, tone on/off, and reports the timer register values for verification |

### R.4.2 Bias, Selection, Acquisition (outline, detailed later)

| ID | Requirement |
|----|-------------|
| FW-11 | DAC80508 driver (SPI): per-channel write, gain/reference configuration, broadcast zero at start-up |
| FW-12 | Pixel selection sequence: heater DACs → 0, mux EN low, set addresses, EN high, ramp heaters; flags X/Y invalid until thermal and filter settling |
| FW-13 | ADS1220 driver: X and Y alternately (AIN0−AIN1, AIN2−AIN3), 20–1000 SPS, DRDY interrupt |
| FW-14 | MCU ADC acquisition of drain sense and heater currents, averaged to ≈ 1 Hz |
| FW-15 | Streaming frames per [§5.6](schematic_overview.md#56-pc-link) |
| FW-16 | Calibration routines: zero offset (mux disabled), dummy-load checks (position 4), optional tone gain/phase |