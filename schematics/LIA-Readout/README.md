# GMOS LIA Board (KiCad project)

KiCad project of the LIA readout board for the GMOS gas sensor.

| Path | Contents |
|------|----------|
| `LIA-Readout.kicad_pro`, `*.kicad_sch`, `*.kicad_pcb` | KiCad project, schematic sheets, layout |
| `device_libraries/` | Project symbol libraries |
| [docs/](docs/README.md) | Design documentation: requirements, schematic overview, task list, decision log, references |
| [../documents/](../documents/) | General documents shared by all boards: measurement principles, application notes, earlier boards. Lab tests and decision records of this board are in [docs/](docs/README.md) |
| [../tools/](../tools/README.md) | Shared netlist query and check tools; this board's expected results are in [../tools/checks/LIA-Readout/](../tools/checks/LIA-Readout/) |
| [../CLAUDE.md](../CLAUDE.md) | Working rules for Claude Code, shared by all schematic projects |

Simulations of the front end are in [`simulations/`](../../simulations/README.md). The MCU firmware project is in [`firmware/`](../../firmware/).
