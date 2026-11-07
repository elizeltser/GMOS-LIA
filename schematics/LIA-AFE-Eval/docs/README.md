# LIA-AFE-Eval — Overview

KiCad project of the analog front-end evaluation board for the GMOS lock-in readout. The board carries the analog chain of [LIA-Readout](../../LIA-Readout/docs/README.md) (sensor socket and selection, excitation drive, bias DAC, front end, two demodulators) and is driven by an external NUCLEO board. It is used on the lab bench to debug the analog chain and the excitation firmware before the production board is built.

> **Status (2026-11-07):** power and demodulator sheets changed (E-12, E-13). Review [2026-11-07](reviews/2026-11-07_schematic_rev0.2.md) A-01 and A-02 fixed in the schematic. Board simulations P-23…P-34 in `simulations/simulation-index.md` (Batch 4). Earlier status:
>
> **Status (2026-10-29):** requirements rev B written ([requirements.md](requirements.md)), parts selected ([component_selection.md](component_selection.md)). Schematic rev 0.1 entered on all sheets; `tools/checks/LIA-AFE-Eval/T01.txt` passes, netcheck clean. Open: the schematic-entry items in §9.2 (to be confirmed by the owner), then design review and layout. Front end fixed to FE-B (decision E-1).

---

## Document Map

| File | Contains | Authoritative for |
|------|----------|-------------------|
| `README.md` (this file) | Overview, document map, decision log, open items | Decisions, open items |
| [requirements.md](requirements.md) | All requirement tables of this board, control header pinout | Target values |
| [component_selection.md](component_selection.md) | Parts per sheet with LCSC numbers, stock and price, stock risks | Part choices |
| [measurement_principles.md](../../documents/measurement_principles.md) | Theory shared with LIA-Readout | Theory and derivations |
| [reviews/](reviews/) | Design reviews: [rev 0.1, 2026-10-29](reviews/2026-10-29_schematic_rev0.1.md), [netlist of 2026-11-07 against the simulations](reviews/2026-11-07_schematic_rev0.2.md) | Review findings |

Documentation rules: [schematics/CLAUDE.md, Documentation Rules](../../CLAUDE.md#documentation-rules).

---

## 9. Decisions & Open Items

### 9.1 Decision Log

Decisions of this board are numbered `E-n`, so they cannot be confused with the LIA-Readout decisions `D-n`.

| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| E-1 | 2026-10-29 | Front end **FE-B only** (±5 V analog, INA828, switch demodulator TMUX6136 + OPA2196), no assembly variants | Owner decision; current provisional recommendation of LIA-Readout D-18 |
| E-2 | 2026-10-29 | Excitation sine and X/Y references come from an external NUCLEO board through headers; the on-board DAC is controlled by the NUCLEO over SPI. No on-board MCU, no jumper-selectable sources | Tests the production excitation firmware together with the analog chain |
| E-3 | 2026-10-29 | Sensor socket and pixel selection as on LIA-Readout (GMOS socket, TMUX1109, R_D, drain bias) | CMRR, leakage and node capacitance are measured on the production circuit |
| E-4 | 2026-10-29 | Analog rails positive and negative; digital parts (DAC interface, mux logic) supplied from the NUCLEO 3.3 V | Owner decision |
| E-5 | 2026-10-29 | Signal-path C0G capacitors ±5 % for the first build, reworked to ±1 % later. Circuit values unchanged from LIA-Readout | ±1 % 33 nF C0G is out of stock at LCSC; owner decision |
| E-6 | 2026-10-29 | TMUX1109 in UQFN-16 (TMUX1109RSVR) instead of TSSOP-16 | TSSOP version has 1 piece at LCSC; same die |
| ~~E-7~~ | 2026-10-29 | ~~One TMUX6136 per demodulator sheet, second switch unused~~. Replaced by E-13 | ~~Keeps the two `DEMODULATOR` instances identical; costs one more TMUX6136~~ |
| E-8 | 2026-10-29 | Drain-path resistors ≤ ±10 ppm/°C (AN-4a) | Owner decision: low drift on the drain |
| E-9 | 2026-10-31 | Post-filter is a Sallen-Key low-pass (R14, R15, C13, C15) with gain placeholders R88 0 Ω and R89 DNP, output centred on 0 V. VMID and VMID_PF dividers removed (R74–R77, C92, C93, TP25); J10 pin 5 not connected. Replaces the inverting −1.5 stage. Differs from LIA-Readout AN-26, so results for this stage do not transfer | Owner decision: no reference divider and its drift, better 2f₀ rejection, no ADC on this board. Scale is 25.5 instead of 38.2 and X has the opposite sign until gain is added |
| E-10 | 2026-10-31 | Drain-sense amplifier U23 and its parts removed (R62–R67, C78–C81), `DSENSE_A/B` and J7 pins 19, 20 unused. TP15 and TP16 reach `DRN_A` and `DRN_B` through R90 and R91, 100 kΩ. Differs from LIA-Readout AN-11 | Owner decision: the drains are checked once at the start, not monitored. Also removes the F-02 overvoltage path into the ADC pins. The value 100 kΩ is an `ASSUMPTION` to be confirmed |
| E-11 | 2026-10-31 | One gate net `GATE` driven by U1B from DAC channel 4 (`GATE_DC`). Stage parts R1–R4, C1, C3, C5, R58 and TP13 removed. U1A is a unity-gain follower with +IN at GND. DAC channel 5 not connected. Replaces LIA-Readout D-17 on this board | Owner decision: simpler bench board. Estimated phase margin 79° at 100 pF, 55° at 1 nF. No gate trim per side: only the drain supplies can null the active/blind DC difference. Follower with input at mid-supply follows TI guidance for an unused op-amp |
| E-12 | 2026-11-07 | Power from two bench supplies: J4 ±15 V for the TMUX6136 (D4, D9, no series resistors), J5 ±5 V for ±5VA (R18, R19) and +5VP (R32), a B5819W in each line. LDOs, rail clamps and the 10 Ω TMUX6136 filters removed. J5 is set so that +5VA = 5.0…5.2 V at TP3. J4 on before J5. Replaces DC-2, DC-3, DC-5 of rev D | Owner decision: simpler bench board, TMUX6136 well inside its rating. The Schottky drop would leave +5VA near 4.6 V at a 5.0 V input, which trips the DAC80508 reference alarm ([review 2026-11-07](reviews/2026-11-07_schematic_rev0.2.md) A-03). The order keeps the TMUX6136 powered whenever signals are present (A-05) |
| E-13 | 2026-11-07 | One `Demod` sheet with the X and Y channels, both on one TMUX6136 (U24). Replaces E-7 and the two-instance sheet of AN-10 | Owner decision: one switch part instead of two (TMUX6136 stock risk, component_selection §C.1). Differs from the one-file-two-instances convention of LIA-Readout |

### 9.2 Open Items

Open questions are tracked in [requirements.md §R.9](requirements.md#r9-open-questions).

Items from schematic entry (2026-10-29), to be confirmed by the owner:

| # | Item | Where | As entered |
|---|------|-------|------------|
| S-1 | Closed by E-9: the VMID and VMID_PF dividers were removed | — | — |
| S-2 | `ASSUMPTION` DAC80508 REF pin capacitor not checked against the datasheet | DAC C70 | 150 nF X7R |
| S-3 | Net names differ from LIA-Readout: IF-5 uses `SPI_SCLK` and `HSENSE_A/B`, LIA-Readout §1.2 uses `SPI_SCK` and `IHTR_A/B` | DAC, Sensor, Connectors | `SPI_SCLK` as IF-5; `IHTR_A/B` = INA190 output, `HSENSE_A/B` = after the 1 kΩ / 100 nF RC |
| S-4 | Status line of rev A named open questions Q-14 (drift scheme) and Q-15 (in-amp); they are not defined in requirements §R.9 | — | INA828 per E-1 and component_selection |
| S-5 | Footprints not given in the documents | DAC U8, J4, J8, J10 | WQFN-16 3 × 3 mm EP 1.68 mm, Phoenix MKDS 5.08 mm 1 × 3, Amphenol 132134 vertical SMA, 1 × 5 pin header; check against the LCSC parts |
| S-6 | General decoupling and bulk capacitors, pull-downs and 10 Ω / 100 Ω resistors have no MPN yet (component_selection §C.9) | All sheets | Values and footprints only |

