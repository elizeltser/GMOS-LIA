# CLAUDE.md — GMOS LIA Board (KiCad project)

KiCad project for the MSc-thesis readout board: a lock-in amplifier for the GMOS gas sensor. Architecture, parts and values are in `docs/` (start with `docs/README.md`); do not restate them here.

The owner edits wiring and layout by hand in the KiCad GUI. Your job is to plan the edits, make the few safe text edits listed below, and **verify** every change against the netlist. The first board spin must work: be conservative, never guess.

## Paths

All commands below run from this folder (the one containing `GMOS-LIA.kicad_pro`):

```bash
DOCS=docs     # design documentation (authoritative): README.md, schematic_review.md, schematic_overview.md, ...
TOOLS=tools   # netquery.py, netcheck.py, checks/
```

Simulations live in `../../simulations/` (start with its `README.md`); the MCU firmware project in `../../firmware/`.

## Read Before Any Work

1. `$DOCS/schematic_review.md` — §0 (task loop), §1 (decisions), §3 (tasks T00–T10). **This is the work list.**
2. `$DOCS/schematic_overview.md` — circuits, values, net names (§1.2), pin map (§5).
3. `$DOCS/README.md` §9 — decision log and open items.
4. `$TOOLS/README.md` — how the netlist tools and check files work.
5. As needed: `$DOCS/requirements.md` (targets), `$DOCS/measurement_principles.md` (theory), `$DOCS/firmware.md` (MCU pins/peripherals the schematic must provide), `$DOCS/decisions/` (decision records), `../../simulations/simulation-plan.md` (simulation requirements, D-18 matrix).

The docs are authoritative for values and topology. If the schematic and the docs disagree and the task list does not say which wins, **stop and ask**.

## Task Loop (one task per session/commit)

1. Pick the next unticked task in `$DOCS/schematic_review.md` §3. If it depends on a decision that is still **open** in its §1, stop and ask.
2. Do the `[CC]` steps yourself (allowed text edits only, see below).
3. Print the `[GUI]` steps as a numbered list with exact designators, pins, net names and values. Wait until the owner says "done, saved".
4. Verify:
   ```bash
   kicad-cli sch export netlist --format kicadsexpr -o GMOS-LIA.net GMOS-LIA.kicad_sch
   python3 $TOOLS/netquery.py GMOS-LIA.net check $TOOLS/checks/Txx.txt
   python3 $TOOLS/netcheck.py GMOS-LIA.net
   kicad-cli sch erc -o erc.rpt GMOS-LIA.kicad_sch
   ```
5. For each failure show the check line, the actual state (`python3 $TOOLS/netquery.py GMOS-LIA.net net <PIN>` / `part <REF>`), and the GUI fix. Repeat 3–5 until the task's check file passes. New `netcheck` findings in the sheets you touched must be fixed or explained; pre-existing ones elsewhere are reported, not fixed.
6. Tick the task in §3, add a line to the log in §5 (date, task, `n/n checks passed`), and propose a commit message `Txx: <title>`. Commit only when the owner agrees.

## Editing Rules

**Allowed text edits in `.kicad_sch`** (KiCad closed, or the owner reloads the sheet afterwards):
- A symbol instance's `Value`, `Footprint`, `Datasheet`, `Description`, `Reference`, or adding an `MPN` property — copy the exact S-expression format of an existing property in the same file.

**Never:**
- Add, move or delete wires, labels, junctions, symbols or sheets by text editing — these are `[GUI]` steps for the owner.
- Edit `.kicad_pcb`, `.kicad_pro`, `fp-lib-table`/`sym-lib-table`, or library files unless the owner asks.
- Change a value the task list does not specify, "improve" a circuit on your own, or re-annotate designators.
- Edit check files to make them pass. A check may be changed only if it is wrong (typo, wrong pin number after verifying the symbol); say so explicitly and show the diff.

## Conventions

- **Values** exactly as in the docs/check files (string compare, e.g. `4.7u`, `100n`, `10k`). Precision parts carry tolerance in a field, not in the value.
- **Footprints and dielectrics**: as the docs specify; when they do not, ask.
- **Net names**: use the target names in `$DOCS/schematic_overview.md` §1.2. Hierarchical labels must be spelled identically on both sides (netcheck reports `SINGLE-NODE` otherwise).
- **Parts**: common and cheap, preferably JLCPCB/LCSC stocked; when a task leaves the choice open, propose 1–2 options with LCSC numbers and stock instead of choosing silently.
- **Designators** must match the docs; if the owner adds parts, use the next free number and record it in the task.

## Netlist Tools (quick reference)

```bash
python3 $TOOLS/netquery.py GMOS-LIA.net net U12:PA4      # net of a pin + members
python3 $TOOLS/netquery.py GMOS-LIA.net part U8          # value/footprint/fields
python3 $TOOLS/netquery.py GMOS-LIA.net check FILE...    # assertions; exit 1 on failure
python3 $TOOLS/netcheck.py GMOS-LIA.net [--mpn]          # whole-netlist sanity scan
```

Pins: `U5.9` (number) or `U12:PA4` (name). On `ambiguous pin name`, use the number. Check-file syntax: `$TOOLS/README.md` §2.3.

Option-dependent checks (e.g. the front-end variants of decision D-18) are separate check files or tagged lines; `$DOCS/schematic_review.md` says which one applies to each task.

## When Unsure

Stop and ask rather than guess — especially about decisions, part substitutions, anything on the drain/gate nodes, and MCU pin functions. Quote the doc section you are relying on in every proposal.