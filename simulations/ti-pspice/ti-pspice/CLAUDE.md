# CLAUDE.md

This folder is an OrCAD Capture / PSpice for TI 23.1 project. It simulates the analog front end of the lock-in amplifier (LIA) used to read the GMOS gas sensor. The excitation and reference frequency is about 517 Hz (parameter `f_osc`). The project is one subfolder of the larger GMOS-LIA repository (see `../../../CLAUDE.md`).

## Where to read first

| Document | Contents |
|---|---|
| `docs/simulation-index.md` | Every simulation, done or planned: goal, schematic, parameters, expected results, status and grade |
| `docs/simulation-quirks.md` | Known traps when running simulations. Read before running anything. |
| `docs/pspice-workflow.md` | Project layout, every file type, how Capture and PSpice fit together, headless runs, reading results, syntax pitfalls |
| `vendor/README.md` | The OPAx192, SPDT_PREC (TMUX6136) and INA828 models: pin orders, parameters, how the designs use them |
| `ti-pspice-PSpiceFiles/LIA/README.md` | Dual-phase switching demodulator (X and Y channels) |
| `ti-pspice-PSpiceFiles/differential-amplifier/README.md` | INA828 input stage with Sallen-Key high-pass and low-pass filters |

Each design README holds the netlist walkthrough, the expected values with their derivation, the latest simulation results and the known issues. Read the relevant one before analysing or changing a design, and update it when you produce new results.

## Designs and profiles

| Design (schematic page) | Profiles | Netlist |
|---|---|---|
| `LIA` | `lia_sanity` (transient with `.STEP` over a parameter) | `ti-pspice-PSpiceFiles/LIA/LIA.net` |
| `differential-amplifier` | `frequency_analysis` (AC), `time_analysis` (transient, `.STEP` over `f`) | `ti-pspice-PSpiceFiles/differential-amplifier/differential-amplifier.net` |

## Running simulations

Always use the runner. It copies the profile into `sim-runs/<name>/`, saves results as text (CSDF) and closes only the PSpice process it started.

```
python tools/run_sim.py <design>/<profile> --name <unique_name> [--probe "V(NODE)" ...] [--analysis "<line>"] [--extra "<line>"]
python tools/run_sim.py circuits/<file>.cir --name <unique_name>
python tools/csdf.py sim-runs/<name>/<name>.csd --list | --summary | --csv out.csv
```

In Python: `sys.path.insert(0, "tools"); from csdf import read_csdf`.

Important behaviour:
- `pspice.exe` is single-instance. While any PSpice window is open (including the user's own), a new run waits. The runner serialises runs with `sim-runs/.pspice.lock`.
- Never kill PSpice by image name (`taskkill /IM pspice.exe`). The user may have it open.
- Node probes need brackets in PSpice (`V([NODE])`). The runner adds them to a bare `V(NODE)`.
- The home-made switch library must be loaded with `.INC`, and signed TI libraries (with a `.LIBsig` file) with `.LIB`. The runner does this. Do the same in hand-written circuits.
- Always set a maximum time step for transients of switching circuits, for example `--analysis ".TRAN 0 1 0 5u SKIPBP"` (the fourth field). The Capture profiles here have none. Without it, PSpice takes too few steps per period, and the LIA output came out about 5.6 % low. Even 20 us leaves a 0.036 % gain error at 517 Hz and 2 % at the 7th harmonic. Use 5u by default and 2u for harmonics or sub-0.01 mV work.
- CSDF values have only four significant digits by default (1 mV resolution near 2.5 V). Add `--extra ".OPTIONS NUMDGT=8"` when you need small differences, ripple or precise DC values.
- Long transients with all nodes saved produce very large `.csd` files. Probe only the nodes you need.
- A `.STEP` run gives one CSDF section per step. `section.step_value` holds the numeric step value.

## Rules for agents

- `TI-PSPICE.DSN` (schematic) and `ti-pspice.opj` (project) are edited only by the user in Capture. Do not modify them, the `.sim` profiles, or the Capture-generated `.net`, `.als` and `.cir` files. Propose schematic changes in words.
- Put hand-written or modified circuits in `circuits/` (tracked by git) with a short comment header saying what the circuit is and how to run it. Analysis scripts that produce reported numbers go in `docs/sim-results/scripts/`. Throw-away scripts go in the session scratchpad.
- `.dat`, `.1OP`, `.mrk` and `.DSN` are binary. Do not try to parse them. Use the `.out` log (netlist echo, bias point, warnings) and CSDF results instead.
- The netlist echoed in a profile's `.out` file is the circuit that was actually simulated. It can differ from the current `.net` after a schematic edit.
- Old results worth keeping go in `archive/<date>_<profile>_<what>/` with a README, because the next GUI run overwrites the profile folder.
- Report numbers with units and with their source (file, or the command that produced them). Write "not verified" for anything you did not check.

## Simulation workflow

Every simulation is an entry in `docs/simulation-index.md`. An entry always states the goal, the schematic that runs, the simulation parameters and the expected results before anything is run. Three roles then handle it, always in this order:

1. **Dispatcher (Haiku, `sim-dispatcher`).** It runs the entry with `tools/run_sim.py` and debugs it until it actually runs. It records every quirk it meets in `docs/simulation-quirks.md`, and returns the result files.
2. **Analyst (Haiku, `sim-analyst`).** It analyses the results against the expected values of the entry and writes `docs/sim-results/<ID>.md`. It then updates the status and result line of the index entry.
3. **Judge (Opus, the main session).** It reviews the summary and the data, and grades the entry with the rubric below. If the grade is below A, it sends the entry back to the dispatcher or the analyst with specific corrections. This repeats until the grade is A, or until the judge records why A is not reachable (for example, a needed schematic change).

PSpice runs one job at a time, so dispatch entries one after another. Analysts can work in parallel with the next dispatch.

### Grading rubric

The judge scores each criterion and gives the lowest of the five as the grade.

| Criterion | A | B | C or below |
|---|---|---|---|
| Correctness | Every number checked against theory or an independent run. Disagreements explained. | Numbers right, one disagreement unexplained. | A wrong number or a wrong conclusion. |
| Method | Settled window, integer periods, settling check and max step all stated and adequate. | One of these missing but harmless. | A method error that affects the result. |
| Reproducibility | Exact commands, run names and analysis scripts recorded. Re-running gives the same numbers. | Commands recorded, a script missing. | Results cannot be reproduced. |
| Completeness | Every expected result of the entry addressed, with pass or fail. | One item missing. | Several items missing. |
| Writing | Follows the writing style below. Tables for numbers. Units everywhere. | Minor style lapses. | Hard to read or ambiguous. |

The judge writes the grade and a one-line justification into the **Grade** field of the index entry.

## Subagents

Defined in `.claude/agents/`:

| Agent | Model | Use |
|---|---|---|
| `sim-dispatcher` | Haiku | Runs an index entry, debugs it until it runs, logs quirks. |
| `sim-analyst` | Haiku | Analyses an entry's results and writes its summary. |
| `netlist-analyst` | Sonnet | Explains a circuit, checks wiring and derives expected values for new index entries. Read-only. |

## Writing style for all project documents

Use simple academic English. Prefer short and medium sentences. Do not join clauses with semicolons, and avoid em dashes. Explain in prose paragraphs. Put parts, parameters and measurements in tables. Use bullet lists only for real lists. Give units for every number. Avoid filler words such as "comprehensive" or "robust".
