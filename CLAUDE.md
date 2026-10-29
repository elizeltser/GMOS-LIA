# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GMOS-LIA is the MSc-thesis project on GMOS (Gas MOS) gas sensors. It contains lab automation for the current bench setup (instruments over GPIB/VISA), the design of a dedicated lock-in readout board, its simulations and firmware, and the LaTeX thesis.

Each area has its own CLAUDE.md with its rules, commands and key files. Read the one for the area you work in before starting. Design values live in the documents those files point to; do not copy them into CLAUDE.md or agent files.

## Areas

| Folder | Contents | Read first |
|--------|----------|------------|
| `ate_lia/` | Python instrument drivers, experiments, MCP server for the bench setup; instrument manuals in `ate_lia/manuals/` | [ate_lia/CLAUDE.md](ate_lia/CLAUDE.md) |
| `schematics/` | KiCad projects with shared rules, conventions and netlist tools (`tools/`, expected results per project in `tools/checks/<project>/`) | [schematics/CLAUDE.md](schematics/CLAUDE.md) |
| `schematics/LIA-Readout/` | KiCad project of the LIA readout board; design docs in `docs/`, background docs in `schematics/documents/` | the doc map [docs/README.md](schematics/LIA-Readout/docs/README.md) |
| `schematics/LIA-AFE-Eval/` | KiCad project of the analog-only test board, later merged into LIA-Readout | [README.md](schematics/LIA-AFE-Eval/README.md) |
| `schematics/documents/existing_boards/` | Earlier GMOS boards (schematic PDFs, Visio drawings, operating procedure) kept as references | — |
| `simulations/` | General simulation documents (plan, index, design context, issues, reviews) and the simulation projects | [simulations/CLAUDE.md](simulations/CLAUDE.md), [simulations/README.md](simulations/README.md) |
| `firmware/` | STM32CubeMX project of the board MCU; specification in `firmware/firmware_requirements.md` | — |
| `thesis/` | LaTeX thesis | [thesis/CLAUDE.md](thesis/CLAUDE.md) |
| `Results/` | Experiment output written by `ate_lia` (git-ignored) | — |

Subagents for the simulation workflow are in `.claude/agents/` and are described in [simulations/ti-pspice/CLAUDE.md](simulations/ti-pspice/CLAUDE.md).

## Where facts live

| Facts | Owner document |
|-------|----------------|
| Board requirements and target values | `schematics/LIA-Readout/docs/requirements.md` |
| Board circuits, values, net names, pins | `schematics/LIA-Readout/docs/schematic_overview.md` |
| Board decisions and open items | `schematics/LIA-Readout/docs/README.md` §9 (evidence in `docs/decisions/`) |
| Simulation baseline values and review limits | `simulations/design-context.md` |
| Bench hardware connectivity, PSU mapping | `ate_lia/FSD.md` |
| MCP safety bounds | `ate_lia/sources/mcp_server/bounds.py` |

The board docs and `simulations/design-context.md` currently disagree on several values (supply, excitation, gain, time constant). Until the owner reconciles them, report any disagreement you rely on instead of choosing.

## Repository-wide rules

- The Python package and its tools are configured in the root `pyproject.toml` (pytest, ruff, pyright). The virtualenv is `.venv/` at the repository root.
- `.mcp.json` starts the `gmos-operating-point` MCP server with paths relative to the repository root; it needs `.venv/` to exist.
- Paths in documentation are relative to the file that contains them, unless the file states otherwise.
