# LIA-AFE-Eval (KiCad project)

Analog front-end evaluation board for the GMOS lock-in readout. It carries only the analog chain (and possibly the bias DACs), is built to be comfortable to use on the lab bench, and is used to debug the analog chain before the production board [LIA-Readout](../LIA-Readout/README.md). The tested circuits are later integrated into LIA-Readout.

| Path | Contents |
|------|----------|
| `LIA-AFE-Eval.kicad_pro`, `*.kicad_sch` | KiCad project and schematic sheets (schematic rev 0.1 entered, layout not started) |
| `device_libraries/` | Project symbol libraries |
| `docs/` | Design documentation: start with [docs/README.md](docs/README.md) (document map), then `requirements.md` |
| [../tools/](../tools/README.md) | Shared netlist query and check tools; this board's expected results are in [../tools/checks/LIA-AFE-Eval/](../tools/checks/LIA-AFE-Eval/README.md) |
| [../CLAUDE.md](../CLAUDE.md) | Working rules for Claude Code, shared by all schematic projects |

## Sheets

| Page | Sheet name | File | Contents |
|------|------------|------|----------|
| 1 | (root) | `LIA-AFE-Eval.kicad_sch` | Sheet symbols and inter-sheet wiring |
| 2 | Power | `POWER.kicad_sch` | ±9 V bench input, reverse-polarity diodes, +5VA, +5VP, −5VA LDOs, rail clamps |
| 3 | Connectors | `CONNECTORS.kicad_sch` | NUCLEO control header (IF-5), X/Y SMA and header (IF-3), test loops, mounting holes |
| 4 | DAC | `DAC.kicad_sch` | DAC80508 bias DAC (AN-6) |
| 5 | Excitation | `EXCITATION.kicad_sch` | Gate excitation drive |
| 6 | Sensor | `SENSOR.kicad_sch` | GMOS socket, pixel selection, drain bias, drain sense, heaters |
| 7 | Front_End | `FRONT_END.kicad_sch` | In-amp and band-pass filter |
| 8 | Demod_X | `DEMODULATOR.kicad_sch` | Synchronous demodulator and post-filter, X channel |
| 9 | Demod_Y | `DEMODULATOR.kicad_sch` | Same file as Demod_X, Y channel |

The sheets were entered from [docs/requirements.md](docs/requirements.md) rev B and [docs/component_selection.md](docs/component_selection.md) on 2026-10-29 (check file `../tools/checks/LIA-AFE-Eval/T01.txt`). Pins are connected by short wire stubs with labels; inter-sheet signals use hierarchical labels, rails use global power symbols. Shared circuits keep the LIA-Readout designators and net names; new parts start at R58, C52, U23, D9, J7, TP1. Simulations of the front end are in [`simulations/`](../../simulations/README.md).
