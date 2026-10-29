# LIA-AFE-Eval — Requirements

This file is the single source for the requirement IDs and target values of the evaluation board. Where a circuit is shared with the production board, the requirement points to the LIA-Readout requirement ([requirements.md](../../LIA-Readout/docs/requirements.md)) instead of copying its value. A reference such as "LIA-Readout AN-21" means that requirement, as it stands in that file. Decisions `E-n` are in [README.md §9.1](README.md#91-decision-log).

**Status of each requirement:** `Agreed` = answered by the owner; `Proposed` = taken from LIA-Readout or suggested, still to be confirmed; `Open` = question in §R.9 not answered yet.

**Change log**

| Rev | Date | Changes |
|-----|------|---------|
| A | 2026-10-29 | Initial set from the first requirements session (block 1: bench use and scope; block 2: power and I/O; block 3: signal chain; block 4: usability) |
| B | 2026-10-29 | Carry-over requirements confirmed; low-drift drain path (AN-4a); control header pinout (IF-5); parts in [component_selection.md](component_selection.md) |

---

## R.0 Purpose and Scope

| ID | Requirement | Status |
|----|-------------|--------|
| BU-1 | The board debugs the analog chain of LIA-Readout on the lab bench before the production board is built. Circuits shared with LIA-Readout are built the same way, so the results transfer | Agreed |
| BU-2 | Front end FE-B only (E-1): ±5 V analog, INA828 in-amp, Sallen-Key band-pass, switch demodulator TMUX6136 + OPA2196, as defined for FE-B in LIA-Readout [schematic_overview §4.9](../../LIA-Readout/docs/schematic_overview.md#49-front-end-architecture-options-decision-d-18). No assembly variants | Agreed |
| BU-3 | No MCU and no ADC on the board. An external NUCLEO board generates the excitation and references and controls the board (E-2) | Agreed |
| BU-4 | No jumper-selectable signal sources. Every function has one fixed signal path | Agreed |
| BU-5 | The board is comfortable to use on the bench: every stage observable with a scope probe, outputs on coaxial connectors, clear silkscreen labels | Agreed (details in R.8) |

## R.1 DC (Power)

| ID | Requirement | Status |
|----|-------------|--------|
| DC-1 | Analog rails positive and negative (±5 V analog for FE-B, E-4) | Agreed |
| DC-2 | Input: dual lab supply ±9 V nominal, operating range ±8…±12 V, on a 3-pin terminal block (+V, GND, −V). Reverse-polarity protection on both inputs. No switching converters on the board | Agreed |
| DC-3 | Analog rails ±5VA from low-noise LDOs fed by the input. TMUX6136 supplied from the input through 10 Ω + 1 µF per supply pin, so VDD − VSS ≥ 10 V (TMUX6136 datasheet SCDS397B §5.4; DI-01 in `simulations/design-issues.md`) | Agreed |
| DC-4 | Digital parts (DAC80508 VDDIO, mux address logic) are supplied from the NUCLEO 3.3 V (E-4). Digital and analog grounds join at one point on the eval board | Agreed |
| DC-5 | Heater rail +5VP from its own LDO, separate from +5VA, as LIA-Readout DC-4b | Agreed |

## R.2 Interfaces

| ID | Requirement | Status |
|----|-------------|--------|
| IF-1 | NUCLEO connection carries: excitation sine (MCU DAC output), X and Y references (timer outputs), SPI to the on-board DAC, mux address/enable lines, 3.3 V and GND | Agreed (signal list) |
| IF-2 | The board does not depend on one NUCLEO model. It has one control header with a fixed pinout (IF-5), connected to the NUCLEO by a cable. The first NUCLEO is the **NUCLEO-F303RE** (STM32F303RET6; ST product page https://www.st.com/en/evaluation-tools/nucleo-f303re.html). Its pin mapping is a cable/firmware matter, not a board change. The excitation firmware on the F303 differs from the STM32U575 production firmware (no GPDMA) | Agreed |
| IF-3 | X and Y demodulator outputs on SMA connectors for the scope, and on a header | Agreed |
| IF-4 | Analog readbacks to NUCLEO ADC pins: drain sense of both sides (buffers as LIA-Readout AN-11) and heater current of both sides (INA190 as LIA-Readout AN-18) | Agreed |
| IF-5 | Control header: keyed 2 × 13 IDC box header, 2.54 mm, pinout in the table below. Ground wires sit next to the excitation and reference lines in the ribbon | Agreed |

**IF-5 control header pinout** (ribbon wire n = pin n)

| Pin | Signal | Dir. (board) | Pin | Signal | Dir. (board) |
|-----|--------|--------------|-----|--------|--------------|
| 1 | GND | — | 2 | `EXC_DAC` (excitation sine) | in |
| 3 | GND | — | 4 | `REF_X` | in |
| 5 | GND | — | 6 | `REF_Y` | in |
| 7 | GND | — | 8 | `SPI_SCLK` | in |
| 9 | `SPI_MOSI` | in | 10 | `SPI_MISO` | out |
| 11 | `DAC_CS` (DAC80508 SYNC) | in | 12 | GND | — |
| 13 | `MUXA_A0` | in | 14 | `MUXA_A1` | in |
| 15 | `MUXB_A0` | in | 16 | `MUXB_A1` | in |
| 17 | `MUX_EN` | in | 18 | GND | — |
| 19 | `DSENSE_A` | out | 20 | `DSENSE_B` | out |
| 21 | `HSENSE_A` | out | 22 | `HSENSE_B` | out |
| 23 | GND | — | 24 | GND | — |
| 25 | +3V3 (from NUCLEO) | in | 26 | +3V3 (from NUCLEO) | in |

## R.3 Excitation (Gate)

| ID | Requirement | Status |
|----|-------------|--------|
| AN-1 | Excitation sine from the NUCLEO DAC, references from NUCLEO timers, generated as in LIA-Readout AN-2 (sine table, square-wave references 90° apart, phase-locked). Firmware behaviour as LIA-Readout FW-1…FW-10, adapted to the NUCLEO in use | Agreed |
| AN-2 | Sine excitation (LIA-Readout AN-2…AN-7b) at the LIA-Readout frequency and band (AN-1, AN-21). Other frequencies need different filter parts (BU-4) | Agreed |
| AN-3 | Gate drive: split gate `GATE_A` / `GATE_B` with MFB summing stages and DC from the DAC, as LIA-Readout AN-3…AN-5 | Agreed |

## R.4 Drain Bias and Heaters

| ID | Requirement | Status |
|----|-------------|--------|
| AN-4 | Drain bias with R_D and coarse/fine DAC trim, as LIA-Readout AN-8…AN-12b | Agreed |
| AN-4a | Every resistor in the drain path is thin film, 0.1 %, ≤ ±10 ppm/°C: R_D, the drain-supply difference amplifier (R_F, R_G), its output filter resistor, R_CAL and the drain-sense gain resistors. Stricter than LIA-Readout AN-8 (≤ 25 ppm/°C) | Agreed |
| AN-5 | Heaters on the board: drivers and current sense as LIA-Readout AN-13…AN-18 | Agreed |
| AN-6 | Bias DAC: DAC80508 controlled by the NUCLEO over SPI (E-2), channel use as LIA-Readout | Agreed |

## R.5 Amplification and Filtering

| ID | Requirement | Status |
|----|-------------|--------|
| AN-7 | Topology and filter as LIA-Readout AN-19, AN-21, AN-22 for FE-B | Agreed |
| AN-8 | In-amp gain G = 10, as LIA-Readout AN-20 | Agreed |
| AN-9 | Noise, CMRR, linear range and drift as LIA-Readout AN-23…AN-23b | Agreed |

## R.6 Demodulation

| ID | Requirement | Status |
|----|-------------|--------|
| AN-10 | Two identical channels X and Y, one schematic sheet used twice (`DEMODULATOR.kicad_sch`) | Agreed |
| AN-11 | Demodulator gain and accuracy as LIA-Readout AN-24, AN-25 for FE-B | Agreed |
| AN-12 | Post-demodulation filter as LIA-Readout AN-26 (τ = 0.5 s). For fast bench tests a smaller capacitor may be fitted by assembly; this is a rework, not an option on the board | Agreed |

## R.7 Channel Selection

| ID | Requirement | Status |
|----|-------------|--------|
| AN-13 | GMOS socket, six pixels, one pair at a time, TMUX1109 selection and calibration loads as LIA-Readout AN-27…AN-29e (E-3). Address and enable lines from the NUCLEO | Agreed |

## R.8 Lab Usability

| ID | Requirement | Status |
|----|-------------|--------|
| LU-1 | Test loops (through-hole loop for a scope probe hook) at every stage output: gate nets, drain nodes, in-amp output, HPF and band-pass outputs, demodulator inputs and outputs, X/Y references, excitation input, all rails. A GND loop next to each group. Coaxial connectors only on X and Y (IF-3) | Agreed |
| LU-2 | Board about 100 mm × 100 mm, M3 mounting holes for standoffs. | Agreed |
| LU-3 | 4-layer PCB with JLCPCB assembly (PCBA) of the SMD parts from LCSC stock. Parts that LCSC does not stock are sourced globally or consigned. Connectors, socket and test loops may be hand-soldered | Agreed |

---

## R.9 Open Questions

Answered questions stay in this table with their answer and the requirement they closed.

| Q | Block | Question | Proposal | Answer |
|---|-------|----------|----------|--------|
| Q-1 | 2 Power and I/O | Coaxial output connector: SMA or BNC? (both were named in session 1) | BNC (scope inputs are BNC, no adapters) | SMA (IF-3) |
| Q-2 | 2 Power and I/O | Power input: which bench supply, voltages, connector? | Dual lab supply ±9 V + LDOs | As proposed (DC-2) |
| Q-3 | 2 Power and I/O | TMUX6136 on ±5 V or ±7 V? | From the filtered ±9 V input | As proposed (DC-3) |
| Q-4 | 2 Power and I/O | NUCLEO model and connection | NUCLEO-U575ZI-Q by cable | NUCLEO-F303RE, by cable to the IF-5 header (IF-2) |
| Q-5 | 2 Power and I/O | Drain-sense and heater-current readbacks to the NUCLEO ADC? | Yes | Yes (IF-4) |
| Q-6 | 2 Power and I/O | Heaters on this board? | Yes, with readbacks | Yes (AN-5, DC-5) |
| Q-7 | 3 Signal chain | Excitation waveform: sine (LIA-Readout AN-2) or square (`simulations/design-context.md` §1)? The documents disagree | Sine | Sine (AN-2) |
| Q-8 | 3 Signal chain | Frequency range: band-pass around 518 Hz (LIA-Readout AN-1, AN-21) or 100 Hz–10 kHz (`design-context.md` §3)? The documents disagree | 518 Hz band-pass | 518 Hz band-pass (AN-2) |
| Q-9 | 3 Signal chain | In-amp gain: 10 (LIA-Readout AN-20) or 11 (`design-context.md` §4)? The documents disagree | 10 | 10 (AN-8) |
| Q-10 | 3 Signal chain | Post-filter τ: 0.5 s (LIA-Readout AN-26) or 0.1 s (`design-context.md` §5)? With the outputs on a scope, a shorter τ may suit the bench better | 0.5 s | 0.5 s (AN-12) |
| Q-11 | 4 Usability | Which test points, and of which type? | Loops at every stage + SMA on key nodes | Loops only (LU-1) |
| Q-12 | 4 Usability | Board size, mounting, shielding | 100 × 100 mm, standoffs, shield-can footprint | 100 × 100 mm, no shield (LU-2) |
| Q-13 | 4 Usability | Assembly and sourcing | JLCPCB PCBA, 4-layer | As proposed (LU-3) |
