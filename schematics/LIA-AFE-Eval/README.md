# LIA-AFE-Eval (KiCad project)

Analog front-end evaluation board for the GMOS lock-in readout. It carries only the analog chain (and possibly the bias DACs), is built to be comfortable to use on the lab bench, and is used to debug the analog chain before the production board [LIA-Readout](../LIA-Readout/README.md). The tested circuits are later integrated into LIA-Readout.

| Path | Contents |
|------|----------|
| `LIA-AFE-Eval.kicad_pro`, `*.kicad_sch` | KiCad project and schematic sheets (layout not started) |
| `device_libraries/` | Project symbol libraries |
| `docs/` | Design documentation (not created yet; start with `docs/README.md` as the document map, then `requirements.md`) |
| [../tools/](../tools/README.md) | Shared netlist query and check tools; this board's expected results are in [../tools/checks/LIA-AFE-Eval/](../tools/checks/LIA-AFE-Eval/README.md) |
| [../CLAUDE.md](../CLAUDE.md) | Working rules for Claude Code, shared by all schematic projects |

## Sheets

| Page | Sheet name | File | Contents |
|------|------------|------|----------|
| 1 | (root) | `LIA-AFE-Eval.kicad_sch` | Sheet symbols and inter-sheet wiring |
| 2 | Power | `POWER.kicad_sch` | Bench supply input, protection, analog rails |
| 3 | Connectors | `CONNECTORS.kicad_sch` | Lab I/O: sensor, excitation and reference inputs, X/Y outputs, test points |
| 4 | DAC | `DAC.kicad_sch` | Sensor bias voltages (optional on this board) |
| 5 | Excitation | `EXCITATION.kicad_sch` | Gate excitation drive |
| 6 | Sensor | `SENSOR.kicad_sch` | GMOS socket, pixel selection, drain bias, heater |
| 7 | Front_End | `FRONT_END.kicad_sch` | In-amp and band-pass filter |
| 8 | Demod_X | `DEMODULATOR.kicad_sch` | Synchronous demodulator and post-filter, X channel |
| 9 | Demod_Y | `DEMODULATOR.kicad_sch` | Same file as Demod_X, Y channel |

All sheets are empty placeholders until the requirements are written. Until this board has its own documents, the LIA-Readout documents ([../LIA-Readout/docs/](../LIA-Readout/docs/README.md)) are the reference for the shared circuits. Simulations of the front end are in [`simulations/`](../../simulations/README.md).
