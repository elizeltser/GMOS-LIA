# CLAUDE.md — Simulations

General simulation documents are in this folder; each simulation project has its own folder. Start with [README.md](README.md), which lists both.

- Board-level simulation requirements and the D-18 decision matrix: [simulation-plan.md](simulation-plan.md).
- Every run, its status and grade: [simulation-index.md](simulation-index.md). Design issues found by simulation: [design-issues.md](design-issues.md); hardware reviews per batch: [design-review/](design-review/).
- Design values and review limits for simulation work: [design-context.md](design-context.md). Board requirements are in `../schematics/LIA-board/docs/requirements.md`. If the two disagree, report it to the user; do not choose.
- PSpice for TI project (workflow, runner, rules; subagents in the repository root `.claude/agents/`): [ti-pspice/CLAUDE.md](ti-pspice/CLAUDE.md). Read it before any PSpice work.
- LTspice drafts: [ltspice/README.md](ltspice/README.md).

Simulators run only on the owner's Windows machine. On other machines, do not run simulations: prepare index entries and run setups for the owner.
