# CLAUDE.md

This folder is an OrCAD Capture / PSpice for TI 23.1 project. It simulates the analog front end of the lock-in amplifier (LIA) used to read the GMOS gas sensor. The project is one subfolder of the larger GMOS-LIA repository (see `../../../CLAUDE.md`).

The design and its requirements are still changing. This file and the agent files in `.claude/agents/` describe the process only. They hold no design values (frequencies, supply, signal levels, part choices, limits). Those live in the project documents listed below, and `docs/design-context.md` is the single source of truth for them. When a design value changes, change it there and nowhere else.

## Where to read first

| Document | Contents |
|---|---|
| `docs/design-context.md` | Requirements, current design baseline, review limits, severity levels and part sourcing rules, each with a status (Fixed, Current, Draft, TBD). Read before any design work. |
| `docs/simulation-index.md` | Every simulation, done or planned: goal, schematic, parameters, expected results, status and grade. Also the default run settings and measurement rules. |
| `docs/simulation-quirks.md` | Known traps when running simulations. Read before running anything. |
| `docs/design-issues.md` | Register of open and closed design issues. Read before changing a design or planning tests. |
| `docs/design-review/` | One design review per batch of simulations, written by the `design-reviewer` agent. |
| `docs/pspice-workflow.md` | Project layout, designs and profiles, every file type, how Capture and PSpice fit together, headless runs, reading results, syntax pitfalls. |
| `vendor/README.md` | The vendor and home-made models: pin orders, parameters, how the designs use them. |
| `ti-pspice-PSpiceFiles/<design>/README.md` | One per design: netlist walkthrough, expected values with their derivation, latest results and known issues. |

Read the relevant design README before analysing or changing a design, and update it when you produce new results. The current designs and their profiles are listed in `docs/pspice-workflow.md`, section 1.

If two documents disagree on a design value, `docs/design-context.md` wins. Report the disagreement to the user instead of silently choosing.

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
- Always set a maximum time step for transients of switching circuits (the fourth field of `.TRAN`). The Capture profiles here have none, and without it the results are wrong. The default step, and the error each step size leaves, are in `docs/simulation-index.md` under "Default run settings" and in `docs/simulation-quirks.md`.
- CSDF values have only four significant digits by default. Add `--extra ".OPTIONS NUMDGT=8"` when you need small differences, ripple or precise DC values.
- Long transients with all nodes saved produce very large `.csd` files. Probe only the nodes you need.
- A `.STEP` run gives one CSDF section per step. `section.step_value` holds the numeric step value.

## Rules for agents

- `TI-PSPICE.DSN` (schematic) and `ti-pspice.opj` (project) are edited only by the user in Capture. Do not modify them, the `.sim` profiles, or the Capture-generated `.net`, `.als` and `.cir` files. Propose schematic changes in words.
- `docs/design-context.md` is edited only on the user's instruction. Agents propose changes to it in words.
- Do not copy design values into agent files, `CLAUDE.md` or new process documents. Refer to `docs/design-context.md` instead. Index entries, summaries and reviews may quote a value, with a reference to its source document.
- Put hand-written or modified circuits in `circuits/` (tracked by git) with a short comment header saying what the circuit is and how to run it. Analysis scripts that produce reported numbers go in `docs/sim-results/scripts/`. Throw-away scripts go in the session scratchpad.
- `.dat`, `.1OP`, `.mrk` and `.DSN` are binary. Do not try to parse them. Use the `.out` log (netlist echo, bias point, warnings) and CSDF results instead.
- The netlist echoed in a profile's `.out` file is the circuit that was actually simulated. It can differ from the current `.net` after a schematic edit.
- Old results worth keeping go in `archive/<date>_<profile>_<what>/` with a README, because the next GUI run overwrites the profile folder.
- Report numbers with units and with their source (file, or the command that produced them). Write "not verified" for anything you did not check.

## Simulation workflow

Every simulation is an entry in `docs/simulation-index.md`. An entry always states the goal, the schematic that runs, the simulation parameters and the expected results before anything is run. Four roles then handle it, always in this order:

1. **Dispatcher (`sim-dispatcher`).** It runs the entry with `tools/run_sim.py` and debugs it until it actually runs. It records every quirk it meets in `docs/simulation-quirks.md`, and returns the result files.
2. **Analyst (`sim-analyst`).** It analyses the results against the expected values of the entry and writes `docs/sim-results/<ID>.md`. It then updates the status and result line of the index entry.
3. **Judge (the main session).** It reviews the summary and the data, and grades the entry with the simulation rubric below. If the grade is below A, it sends the entry back to the dispatcher or the analyst with specific corrections. This repeats until the grade is A, or until the judge records why A is not reachable (for example, a needed schematic change).
4. **Design reviewer (`design-reviewer`).** It runs once per batch, after the judge has graded every entry of the batch. It reviews the circuits and results as hardware, against `docs/design-context.md`. It writes `docs/design-review/<date>_<batch>.md`, updates `docs/design-issues.md`, and proposes new tests (`R-<n>`) and readily available replacement parts. The judge then grades the review with the design review rubric below, in the same loop as for simulation entries.

PSpice runs one job at a time, so dispatch entries one after another. Analysts can work in parallel with the next dispatch.

### Batches and the design review

A batch is the set of index entries run in response to one user request, or in one working session if the user gave no request. A batch has one entry or more. When the last entry of a batch has its grade, the main session must start `design-reviewer` with the list of entry IDs before it reports to the user. Do not skip this step, even for a batch of one entry or when every grade is A. The reviewer also runs when the user asks for a schematic or design review.

The judge grades the review. If the grade is below A, it returns the review to `design-reviewer` with specific corrections, and the reviewer revises the same file. This repeats until the grade is A, or until the judge records why A is not reachable (for example, a requirement that is still TBD). The judge writes the grade and a one-line justification at the top of the review file.

After an A-graded review, the main session does three things:

1. It gives the user the Critical and Major findings, the recommended schematic changes and the open requirement questions, in a short table.
2. It turns the proposed tests it agrees with into planned `P-xx` entries in `docs/simulation-index.md`, keeping the reviewer's expected values. It says in the reply which proposals it did not take, and why.
3. It does not apply schematic changes or requirement changes. The user makes them, in Capture and in `docs/design-context.md`.

### Simulation rubric

The judge scores each criterion and gives the lowest of the five as the grade.

| Criterion | A | B | C or below |
|---|---|---|---|
| Correctness | Every number checked against theory or an independent run. Disagreements explained. | Numbers right, one disagreement unexplained. | A wrong number or a wrong conclusion. |
| Method | Settled window, integer periods, settling check and max step all stated and adequate. | One of these missing but harmless. | A method error that affects the result. |
| Reproducibility | Exact commands, run names and analysis scripts recorded. Re-running gives the same numbers. | Commands recorded, a script missing. | Results cannot be reproduced. |
| Completeness | Every expected result of the entry addressed, with pass or fail. | One item missing. | Several items missing. |
| Writing | Follows the writing style below. Tables for numbers. Units everywhere. | Minor style lapses. | Hard to read or ambiguous. |

The judge writes the grade and a one-line justification into the **Grade** field of the index entry.

### Design review rubric

The judge scores each criterion and gives the lowest of the five as the grade. The judge spot-checks at least the Critical and Major findings against their datasheets and arithmetic.

| Criterion | A | B | C or below |
|---|---|---|---|
| Grounding | Every value comes from `docs/design-context.md`, a project document or a cited datasheet. Draft and TBD values are flagged. Nothing invented. | One value without a source. | An invented requirement or datasheet value. |
| Correctness | Every estimate shows its arithmetic and checks out. Severities follow the levels in `docs/design-context.md`. | One minor estimate wrong, no effect on the severity. | A wrong estimate, mechanism or severity. |
| Coverage | Every checklist category addressed for every circuit in the batch. Known issues updated, not duplicated. | One category missing. | Several missing, or open issues reported again as new. |
| Actionability | Each finding has a concrete change. Proposed tests are complete index entries. Parts follow the sourcing rules, with stock checked and dated. | One finding or test incomplete. | Vague findings, or parts without a stock check. |
| Writing | Follows the writing style below. Tables for numbers. Units everywhere. | Minor style lapses. | Hard to read or ambiguous. |

## Subagents

Defined in `.claude/agents/`. The model of each agent is set in its file.

| Agent | Use |
|---|---|
| `sim-dispatcher` | Runs an index entry, debugs it until it runs, logs quirks. |
| `sim-analyst` | Analyses an entry's results and writes its summary. |
| `netlist-analyst` | Explains a circuit, checks wiring and derives expected values for new index entries. Read-only. |
| `design-reviewer` | Reviews each finished batch as real hardware against `docs/design-context.md`. Proposes tests and available replacement parts (uses the `pcbpart` tools). Writes only to `docs/design-review/` and `docs/design-issues.md`. |

## Writing style for all project documents

Use simple academic English. Prefer short and medium sentences. Do not join clauses with semicolons, and avoid em dashes. Explain in prose paragraphs. Put parts, parameters and measurements in tables. Use bullet lists only for real lists. Give units for every number. Avoid filler words such as "comprehensive" or "robust".