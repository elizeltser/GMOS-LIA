# CLAUDE.md — Schematics (KiCad projects)

This folder holds the KiCad projects of the GMOS lock-in readout and the tools and conventions they share. The rules below apply to every project here. Architecture, parts and values are in each project's documents (listed below). Do not restate them here.

The first board spin must work: be conservative, never guess, and **verify** every schematic change against the netlist.

## Projects and Their Documents

| Project | Purpose | KiCad root | Documents (authoritative) | Expected results |
|---------|---------|------------|---------------------------|------------------|
| `LIA-Readout/` | Production readout board: everything needed to read the GMOS sensor with a lock-in, i.e. analog amplification, filtering and demodulation, ADC, DACs for bias voltages, MCU, DC section and connectors | `LIA-Readout.kicad_pro` | `LIA-Readout/docs/` (start with [README.md](LIA-Readout/docs/README.md), the document map) | `tools/checks/LIA-Readout/` |
| `LIA-AFE-Eval/` | Analog front-end evaluation board: the analog chain (and possibly the DACs) only, built to be comfortable on the lab bench and to debug the analog chain before the production board | `LIA-AFE-Eval.kicad_pro` | `LIA-AFE-Eval/docs/` (start with `README.md`; requirements still to be written). Until then, the LIA-Readout documents are the reference for the shared circuits | `tools/checks/LIA-AFE-Eval/` |

General documents that apply to every board are in `documents/`: measurement principles (theory), application notes (`app_notes/`) and the earlier GMOS boards (`existing_boards/`, reference only, not edited). Board-specific documents (requirements, reviews, task lists, lab tests, decision records) live in the board's own `docs/` folder.

LIA-Readout documents, in reading order:

1. `LIA-Readout/docs/schematic_review.md` — §0 (task loop), §1 (decisions), §3 (tasks T00–T10). **This is the LIA-Readout work list.**
2. `LIA-Readout/docs/schematic_overview.md` — circuits, values, net names (§1.2), pin map (§5).
3. `LIA-Readout/docs/README.md` §9 — decision log and open items.
4. `tools/README.md` — how the netlist tools and check files work.
5. As needed: `LIA-Readout/docs/requirements.md` (targets), `documents/measurement_principles.md` (theory), `LIA-Readout/docs/preliminary_lab_test_results.md` (measured values), `LIA-Readout/docs/decisions/` (decision records), `../firmware/firmware_requirements.md` (MCU pins and peripherals the schematic must provide), `../simulations/simulation-plan.md` (simulation requirements, D-18 matrix).

**LIA-AFE-Eval** is a subset of LIA-Readout. Keep its circuits, net names and, where possible, designators identical to the LIA-Readout counterparts, so the circuits can be copied back without renaming. Any intended difference from LIA-Readout is a decision and is recorded in the LIA-AFE-Eval documents.

The documents are authoritative for values and topology. If a schematic and its documents disagree and the task list does not say which wins, **stop and ask**. If LIA-AFE-Eval and LIA-Readout documents disagree on a shared circuit, report it; do not choose.

Simulations are in `../simulations/` (start with its `README.md`); the MCU firmware project is in `../firmware/`.

## Folder Layout

| Path | Contents |
|------|----------|
| `<project>/` | One KiCad project: `.kicad_pro`, `*.kicad_sch`, `.kicad_pcb`, `device_libraries/` |
| `<project>/docs/` | Documents of that board only: document map, requirements, schematic overview, reviews and task lists, lab tests, decision records (`decisions/`) |
| `documents/` | General documents for all boards: theory, application notes (`app_notes/`), earlier boards (`existing_boards/`) |
| `tools/` | Shared netlist tools `netquery.py`, `netcheck.py` ([README](tools/README.md)) |
| `tools/checks/<project>/` | Expected results: check files of one project, one file per task |

Commands run from the project folder (the one containing the `.kicad_pro`), so the tools are at `../tools/`:

```bash
P=LIA-Readout                     # or LIA-AFE-Eval
CHECKS=../tools/checks/LIA-Readout   # or ../tools/checks/LIA-AFE-Eval
```

## Task Loop (one task per session/commit)

1. Pick the next unticked task in the project's task list (LIA-Readout: `docs/schematic_review.md` §3). If it depends on a decision that is still **open**, stop and ask.
2. Make the schematic edits (see Editing Rules). Steps that are easier or safer in the GUI are printed for the owner as a numbered list with exact designators, pins, net names and values. Wait until the owner says "done, saved".
3. Verify:
   ```bash
   kicad-cli sch export netlist --format kicadsexpr -o $P.net $P.kicad_sch
   python3 ../tools/netquery.py $P.net check $CHECKS/Txx.txt
   python3 ../tools/netcheck.py $P.net
   kicad-cli sch erc -o erc.rpt $P.kicad_sch
   ```
4. For each failure show the check line, the actual state (`python3 ../tools/netquery.py $P.net net <PIN>` / `part <REF>`) and the fix. Repeat 2–4 until the task's check file passes. New `netcheck` or ERC findings in the sheets you touched must be fixed or explained. Pre-existing ones elsewhere are reported, not fixed.
5. Tick the task, add a line to the project's log (date, task, `n/n checks passed`), and propose a commit message `Txx: <title>` (prefix `analog Txx:` for LIA-AFE-Eval). Commit only when the owner agrees.

## Editing Rules

Claude may edit `.kicad_sch` files directly, including wires, labels, junctions, symbols and sheets, under these conditions:
- KiCad has the sheet closed, or the owner reloads it afterwards. Start from a clean `git status` for the files you edit, so each change can be reviewed and reverted with `git diff`.
- Copy the exact S-expression format used elsewhere in the same file. Every new item gets a new unique `uuid`. Wire ends and pin positions sit on the 1.27 mm (50 mil) grid and meet exactly, otherwise KiCad does not connect them. A symbol must exist in the file's `lib_symbols` before an instance uses it.
- After every edit, run the verify step of the task loop. A text edit that KiCad cannot load, or that changes connectivity outside the task, is reverted.
- List what was added, moved or deleted (designators, nets, sheet) so the owner can review it in the GUI.

**Never, unless the owner asks:**
- Edit `.kicad_pcb`, `.kicad_pro`, `fp-lib-table`/`sym-lib-table` or the library files in `device_libraries/`.
- Change a value the task list does not specify, "improve" a circuit on your own, or re-annotate designators.
- Edit check files to make them pass. A check may be changed only if it is wrong (typo, wrong pin number after verifying the symbol). Say so explicitly and show the diff.

## Schematic Conventions

- **Hierarchy**: the root sheet holds only sheet symbols, inter-sheet wiring and power entry. One sheet per functional block. A block used more than once (e.g. the X and Y demodulators) is one `.kicad_sch` file instantiated several times, never a copy. Sheet files are upper case (`DEMODULATOR.kicad_sch`); sheet names are short and unique (`Demod_X`, `Demod_Y`).
- **Page numbers** follow the hierarchy depth-first, without gaps: root = 1, then each sheet in the order it appears on its parent (left to right, top to bottom), with its own sub-sheets directly after it. Renumber after adding or removing a sheet (Schematic Editor → Edit page number, or the `page` field of the sheet instance).
- **Values** exactly as in the docs and check files (string compare, e.g. `4.7u`, `100n`, `10k`). Precision parts carry the tolerance in a field, not in the value.
- **Footprints and dielectrics**: as the docs specify. When they do not, ask.
- **Net names**: use the target names in the project's schematic overview (LIA-Readout: `docs/schematic_overview.md` §1.2). Hierarchical labels must be spelled identically on both sides (`netcheck` reports `SINGLE-NODE` otherwise). Shared circuits use the same net names in both projects.
- **Parts**: common and cheap, preferably JLCPCB/LCSC stocked. When a task leaves the choice open, propose 1–2 options with LCSC numbers and stock instead of choosing silently.
- **Designators** must match the docs. If parts are added, use the next free number and record it in the task.
- **Option-dependent checks** (e.g. the front-end variants of decision D-18) are separate check files or tagged lines. The task list says which one applies.

## Netlist Tools (quick reference)

```bash
python3 ../tools/netquery.py $P.net net U12:PA4      # net of a pin + members
python3 ../tools/netquery.py $P.net part U8          # value/footprint/fields
python3 ../tools/netquery.py $P.net check FILE...    # assertions; exit 1 on failure
python3 ../tools/netcheck.py $P.net [--mpn]          # whole-netlist sanity scan
```

Pins: `U5.9` (number) or `U12:PA4` (name). On `ambiguous pin name`, use the number. Check-file syntax: `tools/README.md` §2.3. New check files go in `tools/checks/<project>/`.

## Documentation Rules

These apply to every document in `<project>/docs/` and `documents/`. A document goes in `documents/` only if it applies to every board; otherwise it goes in the board's `docs/`.

- **One topic per file.** Each fact lives in exactly one file. Other files link to it instead of repeating it. When a fact moves, update the links, not a copy.
- **Document map.** Each project has `docs/README.md` with a document map: file, chapters, contents and what the file is authoritative for. A new document is added to the map in the same change.
- **Global chapter numbers.** Chapter numbers are unique across a project's files, so a reference such as §2.7 is unambiguous. The map lists which file owns each chapter. Links always include the file name, e.g. `[§2.7](measurement_principles.md#27-common-mode-rejection)`.
- **Headings.** Every file starts with `# <Project> — <Topic>` (e.g. `# LIA-Readout — Requirements`; general documents in `documents/` use `# GMOS-LIA — <Topic>`). Chapters are `##`, sections `###`, subsections `####`. No other `#` headings.
- **Requirement IDs** (`DC-n`, `AN-n`, `DG-n`) are defined only in the project's `requirements.md`. Design text quotes the ID, not the value, unless the value is needed for a calculation.
- **Decisions** are numbered `D-n` and logged in the project's `docs/README.md` §9 (date, decision, what it replaces, rationale, where). Longer evidence goes in `<project>/docs/decisions/`. Superseded decisions are struck through and point to their replacement; they are not deleted.
- **Tags:** `TODO` = work to be done; `ASSUMPTION` = value used for sizing, to be confirmed; `DECISION` = a choice recorded in §9.1; `CHANGED` = requirement changed in the current revision (requirements change log).
- **Numbers:** dates `YYYY-MM-DD`. Units with a space (`330 kΩ`, `5 mVpp`). Amplitudes always state `pp`, `pk` or `rms`.
- **Designators** in the text match the netlist. When a part is renamed in KiCad, search the docs and check files for the old designator.
- **Links** are relative to the file that contains them. After moving or deleting a document, search the repository for links to it and fix or remove them in the same change.
- **Style:** simple academic English, short and medium sentences, no filler words. Explain in prose. Put parts, parameters and measurements in tables. Give units for every number.
- **Status:** each project's `docs/README.md` carries a dated status line (what is done, what is open, what gates the next step).

## When Unsure

Stop and ask rather than guess, especially about decisions, part substitutions, anything on the drain/gate nodes, and MCU pin functions. Quote the doc section you are relying on in every proposal.
