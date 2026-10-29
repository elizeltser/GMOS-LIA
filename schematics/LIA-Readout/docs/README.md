# LIA-Readout — Overview

KiCad project for a GMOS gas-sensor readout board based on the lock-in amplifier (LIA) principle. The board replaces the bench setup (SR860 lock-in, SR560 pre-amplifier, lab supplies) used for the 3T differential measurement of the GMOS active/blind transistor pairs.

> **Status (2026-10-28):** schematic capture in progress (netlist 2026-10-24). The front-end architecture (**D-18**: AD630 vs discrete switch demodulator, ±5 V vs single 5 V) is open and is decided from simulations (provisional recommendation in [D-18_frontend.md](decisions/D-18_frontend.md)); the MCU pin/trigger facts (**D-20**) are verified (closed 2026-10-28). Work order and tasks: [schematic_review.md](schematic_review.md). Firmware spec for excitation/references: [firmware_requirements.md](../../../firmware/firmware_requirements.md).

---

## Document Map

Each topic lives in exactly **one** file. Other files link to it instead of repeating it.

| File | Chapters | Contains | Authoritative for |
|------|----------|----------|-------------------|
| `README.md` (this file) | — , 9, 10 | Overview, document map, conventions, decision log, open items, references | Decisions, open items, references |
| [requirements.md](requirements.md) | R | All requirement tables (DC-x, AN-x, DG-x) | Target values (what the board must do) |
| [measurement_principles.md](../../documents/measurement_principles.md) | 2 | Sensing principle, 3T readout, operating point, signal level, noise, CMRR, filter design, gain plan, calibration | Theory and derivations |
| [schematic_overview.md](schematic_overview.md) | 1, 3, 4, 5, 6 | Sheet map, power design, analog design, digital design, power budget | Implemented values (what the schematic does) |
| [simulation-plan.md](../../../simulations/simulation-plan.md) | 7 | Simulation index, required simulations SIM-10…SIM-20 with pass criteria, results, D-18 decision matrix | Simulated values |
| [preliminary_lab_test_results.md](preliminary_lab_test_results.md) | 8 | Lab test procedures and result tables | Measured values |
| [firmware_requirements.md](../../../firmware/firmware_requirements.md) | F | STM32 firmware specification: CubeMX settings, DAC + GPDMA + TIM2/TIM8 excitation and references, module API, verification | Firmware behaviour |
| [schematic_review.md](schematic_review.md) | — | Step-by-step schematic task list (T00–T10) for Claude Code, decisions to confirm, check files in `../../tools/checks/LIA-Readout/` | What still has to change in KiCad |
| [tools/README.md](../../tools/README.md) | — | Netlist tools `netquery.py` / `netcheck.py` and the check-file syntax | — |
| [decisions/](decisions/) | — | Decision records (e.g. `D-18_frontend.md`, `D-18_research.md`, `DC_tps6513x_study.md`) | Evidence behind §9.1 entries |

### Chapter numbering

Chapter numbers are global across files, so a reference such as §2.7 is unique. Links always include the file name, e.g. `[§2.7](../../documents/measurement_principles.md#27-common-mode-rejection)`.

| § | Title | File |
|---|-------|------|
| 1 | Schematic Overview | schematic_overview.md |
| 2 | Measurement Principle & Design Considerations | measurement_principles.md |
| 3 | DC (Power) Section | schematic_overview.md |
| 4 | Analog Section | schematic_overview.md |
| 5 | Digital Section | schematic_overview.md |
| 6 | Power Budget | schematic_overview.md |
| 7 | Simulation | simulation-plan.md |
| 8 | Lab Tests | preliminary_lab_test_results.md |
| 9 | Decisions & Open Items | README.md |
| 10 | References | README.md |
| R | Requirements | requirements.md |
| F | Firmware | firmware_requirements.md |

### Conventions

Headings, requirement IDs, tags, dates, units and designators follow the documentation rules shared by all schematic projects: [schematics/CLAUDE.md, Documentation Rules](../../CLAUDE.md#documentation-rules).

---

## Architecture at a Glance

Two gate groups (pixels 1–3 active, 4–6 blind) are each driven by an MFB stage that adds a DAC80508 DC level to the same MCU-generated sine (DAC1 + GPDMA, paced by TIM2). One active and one blind pixel are selected at a time: per side a TMUX1109 switches the drain supply (coarse/fine DAC bias through R_D = 330 kΩ) and the heater; the in-amp taps the R_D/switch node directly (D-19) → band-pass → X/Y synchronous demodulator (AD630 or discrete switch, D-18) → post-filter → ADS1220; all other pixels are disconnected. TIM8 generates the X/Y square-wave references 90° apart, locked to the DAC timer. The MCU (STM32U575, 16 MHz XO) streams X/Y to the PC over an ISO6721-isolated UART and an external FTDI cable. The block diagram is in [§4.2](schematic_overview.md#42-signal-chain-overview).

---

## 9. Decisions & Open Items

### 9.1 Decision Log

| # | Date | Decision | Replaces | Rationale | Where |
|---|------|----------|----------|-----------|-------|
| D-1 | 2026-10-20 | Documentation split into one-topic-per-file, global chapter numbers | Overlapping README / section files | Removes duplicated and contradictory text | this file |
| D-2 | 2026-10-20 | MCU **STM32U575RGT6** (LQFP64) | STM32G474RET6 | Already in schematic; 14-bit ADC1, 2-ch DAC, low power. LQFP64 has **no VREFBUF** (VREF+ = VDDA), so VDDA is fed from a precision 3.3 V reference | [§5.2](schematic_overview.md#51-mcu-stm32u575rgt6-u12) |
| D-3 | 2026-10-20 | Gate excitation generated by **MCU DAC1_OUT1 + timer + DMA** (sine table), lock-in references from **TIM1 complementary outputs**; frequency, amplitude and phase programmable | Analog quadrature oscillator (sheet `oscillator`) | Adjustable excitation at near-zero BOM cost; exact quadrature; frequency locked to XO; lower THD than the diode-limited oscillator | [§4.5](schematic_overview.md#45-excitation-sheet-analogexcitation) |
| D-4 | 2026-10-20 | MCU clock from a **16 MHz CMOS XO** (±20 ppm) in HSE-bypass mode | (none) | Excitation and references derive from this clock | [§5.3](schematic_overview.md#52-clock) |
| D-5 | 2026-10-20 | ~~3 fixed channels, 2× TMUX6104 on the drain sense nodes only~~ **Superseded by D-12** | 2 channels, 1× TMUX6136 | Pixels 2 (active) and 6 (blind) were not reachable | — |
| D-6 | 2026-10-20 | ~~Bias lines not switched, 6 heater drivers, 6 drain supplies~~ **Superseded by D-12** (based on a misreading: only one pair is operated at a time) | | | — |
| D-7 | 2026-10-20 | ~~2× DAC80508~~ **Superseded by D-13** | | | — |
| D-8 | 2026-10-20 | **PROPOSED:** drain supplies driven directly by the DAC (gain 2, 76 µV LSB), no ×0.4 scaling stage | ×0.4 offset/scaling op-amps (15 µV LSB) | In saturation I_D is set by V_GS and T, so V_supply resolution only sets V_D. Needs confirmation of r₀ (LAB-1/LAB-7) | requirements AN-10 |
| D-9 | 2026-10-20 | Post-demodulator stage = inverting 1st-order LPF (τ = 0.5 s) with gain −3 and level shift to VMID; ADS1220 measures X−VMID, Y−VMID differentially | 2nd-order unity SK with 1 kΩ resistors (schematic) | Matches AN-26, one op-amp per channel, reference errors cancel | [§4.9](schematic_overview.md#49-front-end-architecture-options-decision-d-18) |
| D-10 | 2026-10-20 | Power input via **USB-C PD sink (STUSB4500)**, 12 V PDO; heaters on a separate **+5VP** LDO | Lab supply 11–15 V only; heaters on +5 V analog | Matches schematic sheet `USB_PD`; keeps heater current off the analog rail | [§3.2](schematic_overview.md#31-architecture) |
| D-11 | 2026-10-20 | General-purpose op-amp **OPA2196** (as in schematic) | OPA2192 (docs) | Adequate everywhere after the INA (noise ÷10), much lower I_q. Verify datasheet limits | [§4.4](schematic_overview.md#44-common-components) |
| D-12 | 2026-10-21 | (Principle still valid; mux/R_D implementation superseded by D-16.) **One active/blind pair operated at a time**, all other pixels disconnected. Active = pixels 1–3, blind = 4–6, any combination. 2× TMUX1109 (dual 4:1, one per side, independent address): section A = drain node, section B = heater force; position 4 = calibration (drain) / heater off. R_D (2, matched) on the board side of the mux, drain supply not switched | D-5, D-6; schematic IC1/IC6/IC7 (3× TMUX6136) | Requirement clarified by user. Low R_on (≈ 2 Ω) makes heater switching harmless; only 2 R_D improves matching; one chip per side keeps drain and heater of a pixel switched together | [§4.7](schematic_overview.md#47-pixel-selection-and-calibration-loads) |
| D-13 | 2026-10-21 | **1× DAC80508**: heater A/B, drain supply A/B, gate DC, VMID, 2 spares (one reserved for an optional split gate) | D-7 | 5 bias channels needed; no 5–6 channel 16-bit part is cheaper than one octal; 14-bit octals miss the gate resolution | [§4.6.1](schematic_overview.md#461-dac80508-channel-allocation-as-drawn) |
| D-14 | 2026-10-21 | Power parts: **AO3407A** input P-FET, **SMAJ18A** TVS on connector VBUS, **B5819W** rail clamps, **fixed-voltage ADP7118** (ACPZN5.0 ×2, ACPZN3.3), feedback dividers removed | Generic NMOS, unspecified TVS/diodes, adjustable ADP7118 + dividers | Common, cheap, JLC-stocked parts; fixed LDOs remove six resistors and the divider error | [§3.3](schematic_overview.md#32-component-selection) |
| D-15 | 2026-10-22 | **AD630 gain ±2** (datasheet Rev F Fig. 29, as drawn), no separate ×4 stage, post-filter gain −3; scale factor 38.2·v̂·cos θ at the ADC | AD630 ±1 + ×4 stage (D-9 gain plan) | The drawn configuration is valid (the earlier review item LIA-4 was wrong); saves an op-amp and raises the linear range to 53 mV pk drain differential | [§2.9](../../documents/measurement_principles.md#29-gain-distribution-headroom-and-demodulator-output) |
| D-16 | 2026-10-22 | **Readout topology as drawn:** six R_D on the pixel side, drain supply switched by TMUX1109 bank A, heater by bank B, drain node read by a TMUX1104 per side (shared address per side) | D-12 (two board-side R_D, no TMUX1104) | User's design; equivalent performance, R_D taken from one reel | [§4.7](schematic_overview.md#47-pixel-selection-and-calibration-loads) |
| D-17 | 2026-10-22 | **Split gate:** `GATE_A` (pixels 1–3) and `GATE_B` (4–6), two matched MFB stages fed by the same sine, DAC80508 ch4/ch5 as gate DC | Common gate | Allows trimming active/blind operating points by gate voltage without changing pixel temperature | [§4.5](schematic_overview.md#45-excitation-sheet-analogexcitation) |
| D-18 | open | **Front-end architecture**: FE-A (AD630 ±2, ±5 V, as drawn) / FE-B (TMUX6136 + OPA2196 switch demodulator, ±5 V) / FE-C (single 5 V, V_REF 2.5 V, INA333 + LM7705, 2× TMUX1219, OPA2365). All three give −38.2·v̂·cos θ at the ADC | — | Decide from SIM-10…SIM-20 and the weighted matrix ([simulation-plan.md §7.4](../../../simulations/simulation-plan.md#74-decision-matrix-for-d-18-fill-in-from-73-and-research)); record in [D-18_frontend.md](decisions/D-18_frontend.md) | [§4.9](schematic_overview.md#49-front-end-architecture-options-decision-d-18) |
| D-19 | 2026-10-24 | **Readout muxes IC5/IC6 removed**; the in-amp taps the R_D/switch node | TMUX1104 readout mux per side (D-16) | Fewer parts and less node capacitance; the TMUX1109 bank A already selects the pixel | [§2.6](../../documents/measurement_principles.md#26-front-end-differential-conversion-first) |
| D-20 | 2026-10-28 | **MCU pins as drawn**: SPI1_SCK on PA1 (AF5), TIM8_CH1/CH2 on PC6/PC7 (AF3), TIM2 trigger ITR5 = TIM8 TRGO, DAC trigger T2_TRGO | PB3 for SCK; TIM3 on PC6/PC7 | Verified in the CubeMX 6.16.1 DB; ITR5 = TIM8 is proven on the bench (firmware_requirements.md F.8); CubeMX settings: [firmware_requirements.md §F.2.4](../../../firmware/firmware_requirements.md#f24-cubemx-checklist) | [firmware_requirements.md §F.2.1](../../../firmware/firmware_requirements.md#f21-pin-and-trigger-verification-d-20-closed) |
| D-21 | open | UART: **ISO6721 on board + external FTDI TTL-232R-3V3 cable** on a 6-pin header, no board GND on the header | On-board CP2102N + USB; ISOUSB211 + MCU USB | Simplest isolation; open point: the cable's 5 V VCC on the isolated side (3.3 V LDO or 5 V-tolerant parts) | [§5](schematic_overview.md#5-digital-section) |
| D-22 | 2026-10-26 | **Excitation and references from timers**: DAC1_OUT1 (PA4) with a 128-sample table via GPDMA circular, triggered by TIM2 TRGO (f₀ = 518.03 Hz); TIM8 CH1/CH2 toggle → REF_X/REF_Y (PC6/PC7), 90°, TIM8 starts TIM2 | Analog quadrature oscillator + comparators (D-3); sine references | Exact integer frequency relation, no drift between excitation and references; square-wave references suit both demodulator options | [§2.12](../../documents/measurement_principles.md#212-excitation-and-reference-generation), [firmware_requirements.md](../../../firmware/firmware_requirements.md) |
| D-23 | 2026-10-26 | **Drain bias coarse/fine**: V_SUP = (1+k)·V_coarse − k·V_fine, k = 0.1, 1 kΩ + 10 µF output filter; IC2/IC4 removed | Single DAC channel per drain | 10× finer drain trim with the same DAC | [§2.14](../../documents/measurement_principles.md#214-drain-bias-with-coarse-and-fine-dacs) |

### 9.2 Open Items

| # | Item | Impact | Owner / next step |
|---|------|--------|-------------------|
| 1 | ~~Pixel pairing~~ Closed 2026-10-21: active = 1–3, blind = 4–6, any combination (D-12). Still to do: correct the schematic grouping (review item MUX-3) | — | — |
| 2 | Heater resistance: requirements say 600 Ω–1.2 kΩ, experiment notes say ≈ 300 Ω nominal. At 300 Ω and 4 V the current is 13.3 mA, the 15 Ω shunt drops 200 mV and the INA190A1 output reaches 5 V | Shunt value, INA190 gain, +5VP budget | Measure all 6 heaters with a DMM (LAB-8) |
| 3 | Confirm that the SR860 "5 mV" excitation is rms (bench gain plan assumes 14.1 mVpp) | Signal-level estimate §2.5 | Scope on the gate (LAB-1) |
| 4 | Measure drain AC swing and r₀ at the operating point (LAB-1, LAB-7) | CM level, decision D-8 | Bench |
| 5 | ~~Excitation amplitude vs AD630 headroom~~ Closed 2026-10-22 by D-15: linear up to 53 mV pk drain differential, which covers the full AN-4 range at the expected Δg_m | — | — |
| 6 | Frequency programmability is limited to the fixed band-pass (≈ 400–700 Hz). Decide whether a wider band (or switchable filter) is wanted | AN-1, AN-21 | Decide |
| 7 | ~~PC-link connector~~ Closed by D-21 (ISO6721 + FTDI cable); remaining: cable VCC handling | J6 | T08 |
| 8 | Verify INA828 input CM range / output swing at G = 10 on ±5 V with drains at 0–0.5 V | Front-end headroom | TI calculator |
| 9 | Second-source / stock check: TMUX1109PWR has only ≈ 22 pcs at JLC (≈ USD 3.5), order from TI/Mouser/DigiKey; DAC80508 (low distributor stock), STM32U575RGT6, AD630 | Procurement | Distributor APIs were unavailable on 2026-10-20 |
| 10 | Readout-mux on-capacitance (TMUX1104 ≈ 35 pF typ.) puts the drain readout node at ≈ 50–60 pF, not the 20 pF assumed in §2.6/§2.7. Capacitive CM→DM leakage scales with ω·R_D·ΔC: ≈ 44 dB for a ±10 % (6 pF) mismatch vs ≈ 53 dB at 20 pF. It is mostly quadrature (Y) and static, so the on-board CM calibration can subtract it | System CMRR, AN-23 | Re-run SIM-2 with 60 pF; keep both drain paths strictly symmetric; measure in LAB-6/LAB-10 |
| 11 | VDDA source (D-D): ferrite from +3V3_D (as drawn) vs precision reference | Excitation amplitude stability AN-7, DC-4c | Decide before routing the MCU sheet |
| 12 | AD630 availability: ≈ USD 54 and not stocked at LCSC/JLC (2026-10-24); single source | D-18 | Research R1 in the D-18 prompt |
| 13 | OPA2196 input transition region ≈ 2.0–3.5 V on a 5 V rail: unsuitable around V_REF = 2.5 V in FE-C → OPA2365 (zero-crossover). In FE-B (±5 V) keep its inputs below +2 V | D-18, FE-C BOM | SIM-11 with both models |
| 14 | ~~MCU pins/triggers not yet confirmed from ST data~~ **Closed 2026-10-28** by D-20; remaining CubeMX settings: [firmware_requirements.md §F.2.4](../../../firmware/firmware_requirements.md#f24-cubemx-checklist) | Schematic (pins) and firmware | — |

---

## 10. References

Local copies are kept in `../../documents/app_notes/` and `datasheets/` (paths relative to those folders; files not yet downloaded are listed where they are expected). Instrument manuals are in `../../../ate_lia/manuals/` (the §10.3 paths below are relative to the repository root).

### 10.1 Application Notes & Papers

| ID | Document | Local file | Online |
|----|----------|------------|--------|
| <a id="ref-a1"></a>A1 | *Working With Inverting Buck-Boost Converters*, TI SNVA856B | `app_notes/snva856b.pdf` | [ti.com](https://www.ti.com/lit/an/snva856b/snva856b.pdf) |
| <a id="ref-a2"></a>A2 | R. Mancini, *Design of op amp sine wave oscillators*, TI SLYT164 (historical: oscillator no longer used, D-3) | `app_notes/slyt164.pdf` | [ti.com](https://www.ti.com/lit/an/slyt164/slyt164.pdf) |
| <a id="ref-a4"></a>A4 | ADI Analog Dialogue, *Synchronous detectors facilitate precision, low-level measurements* | `app_notes/` | [analog.com](https://www.analog.com/en/resources/analog-dialogue/articles/synchronous-detectors-facilitate-precision.html) |
| <a id="ref-a5"></a>A5 | J. Williams, LT AN9 *Application considerations and circuits for a new chopper-stabilized op amp* (contains synchronous-rectifier circuits) | `app_notes/an09f.pdf` | [analog.com](https://www.analog.com/media/en/technical-documentation/application-notes/an09f.pdf) |
| <a id="ref-a3"></a>A3 | ST AN3126, *Audio and waveform generation using the DAC in STM32 products* (generic STM32 note; check register names against RM0456 for the U5) | `app_notes/an3126.pdf` | st.com |

### 10.2 Component Datasheets

| ID | Component | Function on board | Local file |
|----|-----------|-------------------|------------|
| <a id="ref-d1"></a>D1 | LMR51430 (TI) | +7 V buck, −7 V IBB | `datasheets/lmr51430.pdf` |
| <a id="ref-d2"></a>D2 | ADP7118 (ADI) | +5VA, +5VP, +3V3_D LDOs | `datasheets/adp7118.pdf` |
| <a id="ref-d3"></a>D3 | LT3094 (ADI) | −5 V LDO | `datasheets/lt3094.pdf` |
| <a id="ref-d4"></a>D4 | AD630 (ADI) | Balanced demodulator | `datasheets/ad630.pdf` |
| <a id="ref-d5"></a>D5 | OPA2196 / OPA2192 (TI) | General-purpose op-amp | `datasheets/opa2196.pdf` |
| <a id="ref-d6"></a>D6 | INA828 (TI) | Instrumentation amplifier | `datasheets/ina828.pdf` |
| <a id="ref-d7"></a>D7 | TMUX1109, TMUX1104 (TI) | Supply/heater and readout multiplexers | `datasheets/tmux1109.pdf`, `tmux1104.pdf` |
| <a id="ref-d8"></a>D8 | DAC80508 (TI) | Gate / heater / drain / VMID DACs | `datasheets/dac80508.pdf` |
| <a id="ref-d9"></a>D9 | ADS1220 (TI) | X/Y ADC | `datasheets/ads1220.pdf` |
| <a id="ref-d10"></a>D10 | INA190 (TI) | Heater current sense | `datasheets/ina190.pdf` |
| <a id="ref-d11"></a>D11 | ISO6721 (TI) | UART isolator | `datasheets/iso6721.pdf` |
| <a id="ref-d12"></a>D12 | TMP117 (TI) | Temperature sensor | `datasheets/tmp117.pdf` |
| <a id="ref-d13"></a>D13 | STM32U575xx datasheet DS13737 + RM0456 (ST) | MCU | `datasheets/stm32u575.pdf` |
| <a id="ref-d14"></a>D14 | SHT40 (Sensirion) | Humidity / temperature | `datasheets/sht4x.pdf` |
| <a id="ref-d15"></a>D15 | CP2102N (Silicon Labs) | USB-UART bridge | `datasheets/cp2102n.pdf` |
| <a id="ref-d16"></a>D16 | STUSB4500 (ST) | USB-C PD sink controller | `datasheets/stusb4500.pdf` |
| <a id="ref-d18"></a>D18 | AO3407A (AOS), SMAJ18A, B5819W | Input P-FET, TVS, rail clamps | `datasheets/` |
| <a id="ref-d17"></a>D17 | ADR4533 (ADI) | VDDA precision reference | `datasheets/adr4533.pdf` |
| <a id="ref-d19"></a>D19 | TMUX6136, TMUX1219 (TI) | Switch demodulator (FE-B / FE-C) | `datasheets/tmux6136.pdf`, `tmux1219.pdf` |
| <a id="ref-d20"></a>D20 | INA333, LM7705, REF3325, OPA2365 (TI) | FE-C single-supply front end | `datasheets/` |

### 10.3 Instrument Manuals

| ID | Instrument | Local file | Online |
|----|------------|------------|--------|
| <a id="ref-m1"></a>M1 | SR860 lock-in amplifier (SRS) | `ate_lia/manuals/SR860m.pdf` | [manual](https://www.thinksrs.com/downloads/pdfs/manuals/SR860m.pdf) |
| <a id="ref-m2"></a>M2 | SR560 low-noise preamplifier (SRS) | not in repo | [manual](https://www.thinksrs.com/downloads/pdfs/manuals/SR560m.pdf) |