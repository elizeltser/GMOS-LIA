# Simulations

Entry point for all simulation work on the GMOS LIA readout. General documents are in this folder. Each simulation project has its own folder with its own README or CLAUDE.md.

## General documents

| File | Contents |
|------|----------|
| [simulation-plan.md](simulation-plan.md) | Board-level plan: what must be simulated (`SIM-xx`), setups, pass criteria, results table and the D-18 decision matrix |
| [simulation-index.md](simulation-index.md) | Every run, done or planned (`C-xx`, `P-xx`): goal, circuit, parameters, expected results, status, grade |
| [design-context.md](design-context.md) | Design values and review limits used by the simulation workflow (status Fixed / Current / Draft / TBD) |
| [design-issues.md](design-issues.md) | Register of design issues found by simulation and review (`DI-xx` of the simulation workflow) |
| [design-review/](design-review/) | One hardware review per batch of runs, with its calculation scripts |

The board's requirements, theory and schematic are in [`schematics/LIA-Readout/docs/`](../schematics/LIA-Readout/docs/README.md). When a value in [design-context.md](design-context.md) disagrees with the board docs, report it instead of choosing.

## Simulation projects

| Folder | Tool | Contents |
|--------|------|----------|
| [ti-pspice/](ti-pspice/CLAUDE.md) | OrCAD Capture / PSpice for TI (Windows) | LIA front end and switch demodulator: Capture project, hand-written netlists in `circuits/`, headless runner, per-run results in `docs/sim-results/` |
| [ltspice/](ltspice/README.md) | LTspice | Early drafts (oscillator, filter, AD630 demodulator) and the GMOS transistor model |

## Adding a simulation

1. Add or update the `SIM-xx` requirement in [simulation-plan.md](simulation-plan.md) if it is a board-level question.
2. Add an index entry (`P-xx`) in [simulation-index.md](simulation-index.md) with goal, circuit, parameters and expected results before running.
3. Put circuits, scripts and the per-run result file in the project folder that runs it, and link them from the index entry.
