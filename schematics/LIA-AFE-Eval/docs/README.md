# LIA-AFE-Eval — Overview

KiCad project of the analog front-end evaluation board for the GMOS lock-in readout. The board carries the analog chain of [LIA-Readout](../../LIA-Readout/docs/README.md) (sensor socket and selection, excitation drive, bias DAC, front end, two demodulators) and is driven by an external NUCLEO board. It is used on the lab bench to debug the analog chain and the excitation firmware before the production board is built.

> **Status (2026-10-29):** requirements rev B written ([requirements.md](requirements.md)), parts selected ([component_selection.md](component_selection.md)). Schematic rev 0.1 entered on all sheets; `tools/checks/LIA-AFE-Eval/T01.txt` passes, netcheck clean. Open: the schematic-entry items in §9.2 (to be confirmed by the owner), then design review and layout. Front end fixed to FE-B (decision E-1).

---

## Document Map

| File | Contains | Authoritative for |
|------|----------|-------------------|
| `README.md` (this file) | Overview, document map, decision log, open items | Decisions, open items |
| [requirements.md](requirements.md) | All requirement tables of this board, control header pinout | Target values |
| [component_selection.md](component_selection.md) | Parts per sheet with LCSC numbers, stock and price, stock risks | Part choices |
| [measurement_principles.md](../../documents/measurement_principles.md) | Theory shared with LIA-Readout | Theory and derivations |

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
| E-7 | 2026-10-29 | One TMUX6136 per demodulator sheet, second switch unused | Keeps the two `DEMODULATOR` instances identical; costs one more TMUX6136 |
| E-8 | 2026-10-29 | Drain-path resistors ≤ ±10 ppm/°C (AN-4a) | Owner decision: low drift on the drain |

### 9.2 Open Items

Open questions are tracked in [requirements.md §R.9](requirements.md#r9-open-questions).

Items from schematic entry (2026-10-29), to be confirmed by the owner:

| # | Item | Where | As entered |
|---|------|-------|------------|
| S-1 | `ASSUMPTION` VMID and post-filter reference dividers: values not given in the documents | Front_End R74–R77, C92, C93 | VMID = +5VA × 10k/(10k+10k) + 100 nF; VMID_PF = VMID × 100k/(150k+100k), 0.1 %, + 100 nF. X/Y outputs centre on VMID because VMID_PF is derived from VMID |
| S-2 | `ASSUMPTION` DAC80508 REF pin capacitor not checked against the datasheet | DAC C70 | 150 nF X7R |
| S-3 | Net names differ from LIA-Readout: IF-5 uses `SPI_SCLK` and `HSENSE_A/B`, LIA-Readout §1.2 uses `SPI_SCK` and `IHTR_A/B` | DAC, Sensor, Connectors | `SPI_SCLK` as IF-5; `IHTR_A/B` = INA190 output, `HSENSE_A/B` = after the 1 kΩ / 100 nF RC |
| S-4 | Status line of rev A named open questions Q-14 (drift scheme) and Q-15 (in-amp); they are not defined in requirements §R.9 | — | INA828 per E-1 and component_selection |
| S-5 | Footprints not given in the documents | DAC U8, J4, J8, J10 | WQFN-16 3 × 3 mm EP 1.68 mm, Phoenix MKDS 5.08 mm 1 × 3, Amphenol 132134 vertical SMA, 1 × 5 pin header; check against the LCSC parts |
| S-6 | General decoupling and bulk capacitors, pull-downs and 10 Ω / 100 Ω resistors have no MPN yet (component_selection §C.9) | All sheets | Values and footprints only |

