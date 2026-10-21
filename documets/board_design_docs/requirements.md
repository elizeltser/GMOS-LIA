# GMOS LIA Board — Requirements

This file is the single source for requirement IDs and target values. Design chapters ([schematic_overview.md](schematic_overview.md)) describe how each requirement is met; theory is in [measurement_principles.md](measurement_principles.md).

**Change log**

| Rev | Date | Changes |
|-----|------|---------|
| A | 2026-09 | Initial set (2 channels, analog oscillator, STM32G474) |
| B | 2026-10-20 | `CHANGED`: AN-1…AN-7b (MCU-generated, programmable excitation), AN-5 (gate DAC direct), AN-10 (proposed relaxation), AN-11/AN-32 (14-bit ADC), AN-12/AN-17, AN-13 (Kelvin wording), AN-15 (16-bit), AN-18 (shunt depends on open item 2), AN-26 (implementation), AN-27…AN-29e (channel selection + CAL), DC-1 (USB-C PD), DC-4b (new +5VP), DG-1, DG-6, DG-7…DG-9 (new) |
| C | 2026-10-21 | `CHANGED`: one active/blind pair operated at a time, others disconnected (active 1–3, blind 4–6): AN-8, AN-12, AN-17, AN-27…AN-29e, AN-31, DG-1 |

---

## R.1 DC (Power)

| ID | Parameter | Value |
|----|-----------|-------|
| DC-1 | Input | `CHANGED` USB-C PD sink, fixed 12 V PDO (15 V acceptable); operating input range 11–15 V. Board must not start the converters on a 5 V-only source. Optional lab-supply input (open item, README §9.2) |
| DC-2 | Intermediate rails (buck / IBB) | ≈ +7 V / ≈ −7 V (reduces LDO dissipation) |
| DC-3 | Max ripple on intermediate rails | 10 % of rail voltage (design achieves < 0.2 %) |
| DC-4 | Analog rails | +5VA, −5VA (linear regulated) |
| DC-4a | Rail-reversal protection | Schottky diodes from +5VA to GND and from GND to −5VA |
| DC-4b | Heater rail | `CHANGED` (new) +5VP, linear regulated, separate from +5VA, supplies the heater drivers |
| DC-4c | MCU analog supply | `CHANGED` (new) VDDA = 3.3 V from a precision reference (≤ 10 ppm/°C, ≥ 5 mA); it is also the MCU DAC/ADC reference |
| DC-5 | Digital rail | +3V3_D (linear regulated) |
| DC-6 | Load current per rail | See [§6](schematic_overview.md#6-power-budget) (values with 1.5× margin) |
| DC-7 | Converter switching mode | Forced PWM (fixed frequency) at all loads, so no burst frequencies fall in the 377–711 Hz signal band |

---

## R.2 Analog

### R.2.1 Excitation (Gate)

| ID | Parameter | Value |
|----|-----------|-------|
| AN-1 | Excitation frequency | `CHANGED` Programmable, default 518 Hz. Usable range set by the band-pass (≈ 400–700 Hz). Resolution ≤ 0.5 Hz. Accuracy and stability follow the MCU clock (DG-7, ±20 ppm) |
| AN-2 | Excitation source and references | `CHANGED` Sine from MCU DAC1_OUT1 (timer-triggered DMA table, ≥ 64 samples/period) followed by a reconstruction low-pass. In-phase (X) and quadrature (Y) lock-in references are square waves from the same timer base, 90° apart, phase-coherent with the sine |
| AN-3 | Gate voltage | Summing op-amp output: AC excitation + gate DC (AN-5). One gate net for all six pixels (optional split into active/blind gate nets, schematic_overview §4.6.1) |
| AN-4 | Gate AC amplitude | `CHANGED` Programmable 0.5–20 mVpp, default 5 mVpp. Amplitude set in firmware (table scaling); fixed analog attenuation ≈ 1/120 |
| AN-5 | Gate DC range / resolution | `CHANGED` 0.97–1.2 V, ≤ 100 µV resolution. One DAC80508 channel (16-bit, 0–2.5 V, 38 µV LSB) through the unity-gain summing amp; offset/drift calibrated |
| AN-6 | Reference levels | `CHANGED` References drive the AD630 comparator inputs differentially (CHn/CHnN, 0/3.3 V), inside the comparator range (−2 V to +3.5 V at ±5 V) |
| AN-7 | Excitation stability | `CHANGED` Frequency ±50 ppm (clock-derived). Amplitude stability ≤ 100 ppm/°C, set by the VDDA reference (DC-4c) and the attenuator resistors (0.1 %, ≤ 25 ppm/°C) |
| AN-7a | Monitoring | `CHANGED` AD630 B/Ā comparator outputs routed to MCU timer inputs to verify reference timing; excitation frequency is known by construction |
| AN-7b | Excitation distortion | `CHANGED` THD ≤ 0.3 % at 5 mVpp (12-bit DAC, ≥ 64 samples/period, reconstruction LPF) |

### R.2.2 Drain Bias

| ID | Parameter | Value |
|----|-----------|-------|
| AN-8 | Topology | `CHANGED` One DAC channel per side (active, blind) through R_D = 330 kΩ (0.1 %, ≤ 25 ppm/°C, thin film, matched pair) to the drain node; R_D on the board side of the pixel mux |
| AN-9 | Voltage range | 2.7–3.5 V |
| AN-10 | Voltage resolution | `CHANGED` **PROPOSED (D-8):** ≤ 100 µV (DAC80508 gain 2, 76 µV LSB, no scaling stage). Rationale: in saturation (V_DS > 3k_BT/q) I_D is set by V_GS and T, so V_supply resolution sets V_D, not I_D. **Fallback** (if LAB-7 shows strong V_DS dependence of I_D): ×0.4 scaling stage, ≈ 15 µV LSB, as in Rev A |
| AN-11 | Current measurement | `CHANGED` Each drain of the selected channel: high-Z buffer with gain 8 → RC LPF (≈ 1 Hz) → MCU ADC1 (14-bit, VDDA = 3.3 V). ≈ 25 µV/LSB at the drain → ≈ 76 pA/LSB; I_D = (V_supply − V_D)/R_D |
| AN-12 | Drain outputs | `CHANGED` 2 DAC channels (active side, blind side), applied to the selected pixels through the mux; drains of unselected pixels are open |
| AN-12a | Drain operating point | I_D 5–10 µA → drain node 50–250 mV DC. With heaters on, firmware keeps V_DS above 3·k_B·T/q at pixel temperature plus half the AC swing ([§2.4](measurement_principles.md#24-transistor-operating-point)) |
| AN-12b | Drain DC mismatch (active − blind) | ≤ ±200 mV (INA DC headroom). Firmware nulls it with the two drain-supply DACs |

### R.2.3 Heaters

| ID | Parameter | Value |
|----|-----------|-------|
| AN-13 | Topology | DAC + op-amp driver per side (switched to the selected pixel), DC voltage; feedback taken at the heater side of the current shunt (Kelvin) so the shunt drop is inside the loop |
| AN-14 | Voltage range | 2.5–4.0 V |
| AN-15 | DAC resolution | `CHANGED` 16-bit (12-bit gives ≈ 0.2 K heater steps at 300 °C, too coarse for current matching) |
| AN-16 | Heater resistance | 600 Ω–1.2 kΩ → 2.1–6.7 mA. `ASSUMPTION`, conflicts with "≈ 300 Ω nominal" in the experiment notes (README §9.2 item 2) |
| AN-17 | Heater outputs | `CHANGED` 2 channels (active side, blind side), switched to the selected pixels; heaters of unselected pixels are open (off) |
| AN-18 | Current measurement accuracy | ≤ 100 µA. INA190A1 (G = 25) + shunt; shunt ≤ 100 mV drop at maximum current (15 Ω for ≤ 6.7 mA, 7.5 Ω if 300 Ω heaters are confirmed). INA190 supplied from 3.3 V so its output cannot exceed the MCU ADC range |

### R.2.4 Amplification & Filtering

| ID | Parameter | Value |
|----|-----------|-------|
| AN-19 | Topology | Instrumentation amplifier (DC-coupled, high-Z inputs) → 2nd-order Sallen-Key HPF → 2nd-order Sallen-Key LPF → non-inverting gain stage → AD630 |
| AN-20 | Gain at f₀ | 40 V/V total: INA 10 × filters 1 × gain stage 4 ([§2.9](measurement_principles.md#29-gain-distribution-headroom-and-demodulator-output)) |
| AN-21 | Bandwidth | f₀ = 518 Hz, −3 dB band 377–711 Hz (section Q = 1) |
| AN-22 | Filter slopes | 40 dB/decade on each side |
| AN-23 | Noise / CMRR | Input-referred amplifier noise < 20 nV/√Hz (well below the ≈ 520 nV/√Hz transistor shot noise, [§2.11](measurement_principles.md#211-noise-and-snr)). INA CMRR ≥ 80 dB at f₀; system CMRR ≥ 48 dB (99 %) |
| AN-23a | Linear input range | Differential drain signal ≤ 20 mV pk, set by the AD630 ±0.8 V design limit. Firmware limits excitation amplitude accordingly |

### R.2.5 Demodulation (Lock-in)

| ID | Parameter | Value |
|----|-----------|-------|
| AN-24 | Demodulator | AD630 pair (X and Y), ±5 V supply, square-wave references (AN-2) |
| AN-25 | AD630 gain | ±1 |
| AN-26 | Post-demodulation filter | τ = 500 ms (first order, f_c = 0.318 Hz), gain 3, output centred on VMID; ADC measures X−VMID and Y−VMID differentially. Longer time constants in software |

### R.2.6 Channel Selection

| ID | Parameter | Value |
|----|-----------|-------|
| AN-27 | Channels | `CHANGED` 6 pixels: active 1–3, blind 4–6. One pair (one active + one blind, any combination) is operated at a time; the others are disconnected. Plus one calibration position |
| AN-28 | Selection | `CHANGED` Two identical dual 4:1 precision multiplexers, one per side, with independent address and enable |
| AN-29 | Switched signals | `CHANGED` Per pixel: drain node and heater force line, switched together. Gate is common (not switched). Drain supply and R_D are on the board side and not switched |
| AN-29a | Switched signal level | Drain: 50–250 mV DC + up to ≈ 400 mVpp at f₀. Heater: 0–4.0 V DC, ≤ 6.7 mA (≤ 13.3 mA if 300 Ω heaters are confirmed) |
| AN-29b | Switch on-resistance | ≤ 5 Ω (heater path: ≤ 35 mV drop, stable; drain path uncritical in series with 330 kΩ) |
| AN-29c | Switch leakage | ≤ 100 pA (≤ 33 µV DC error at the drain node) |
| AN-29d | Other switch parameters | Signal range 0–4.5 V on a single +5VA supply, continuous current ≥ 15 mA per channel, 3.3 V logic, break-before-make, matched capacitance (same part both sides), enable pin for all-off at power-up |
| AN-29e | Calibration input | `CHANGED` (new) Mux position 4 (drain section; heater section open) carries an on-board test tone from MCU DAC1_OUT2 (differential tone, matched DC) for gain/phase calibration of the whole chain |

### R.2.7 Data Converters

| ID | Parameter | Value |
|----|-----------|-------|
| AN-30 | X/Y ADC | 24-bit ΔΣ, 2 differential inputs, SPI, 20–1000 SPS, ±2.048 V full scale |
| AN-31 | Heater current ADC | `CHANGED` MCU ADC (12/14-bit), 2 channels, must meet AN-18 |
| AN-32 | Drain current ADC | `CHANGED` MCU ADC1 (14-bit) with ×8 front end, must meet AN-11 |

### R.2.8 Miscellaneous

| ID | Parameter | Value |
|----|-----------|-------|
| AN-33 | GMOS package ESD protection | Supplied from +5VA, ≈ 5 mA |

---

## R.3 Digital

| ID | Requirement |
|----|-------------|
| DG-1 | `CHANGED` MCU STM32U575RGT6 controlling all DACs, ADCs, pixel selection (6 GPIO) and excitation |
| DG-2 | Digital temperature sensor: COTS, readily available, open-source drivers |
| DG-3 | Digital humidity sensor: same criteria as DG-2 |
| DG-4 | Serial link to PC: command/response plus streamed samples ([§5.6](schematic_overview.md#56-pc-link)), galvanically isolated from the analog ground, on its own USB data connector |
| DG-5 | SWD connector for MCU programming (10-pin Cortex debug header) |
| DG-6 | `CHANGED` MCU internal ADC1 (14-bit) for drain sense; ADC1/ADC4 for heater currents and housekeeping |
| DG-7 | `CHANGED` (new) MCU clock from an external CMOS oscillator (XO), 16 MHz, ±20 ppm, HSE bypass. Not a bare crystal |
| DG-8 | `CHANGED` (new) MCU DAC1_OUT1 = gate excitation, DAC1_OUT2 = calibration tone. Both reserved for these functions |
| DG-9 | `CHANGED` (new) USB-C PD controller configurable from the MCU over I²C (PDO selection, status) |
