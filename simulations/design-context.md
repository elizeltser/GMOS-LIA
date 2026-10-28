# Design context and requirements

> **Paths.** Paths that start with `simulations/` are relative to the repository root. All other backticked paths (`circuits/`, `tools/`, `ti-pspice-PSpiceFiles/`, `vendor/`, `archive/`, `docs/`) are relative to the PSpice for TI project, [`ti-pspice/`](ti-pspice/CLAUDE.md).

This file is the single source of truth for the design values of the GMOS lock-in front end: requirements, the current design baseline, review limits and part sourcing rules. Agent definitions in the repository root `.claude/agents/` and the CLAUDE.md files do not repeat these values. They point here.

The design is still changing and many requirements are not settled. Each value therefore has a status:

| Status | Meaning |
|---|---|
| Fixed | Agreed. Change only with the user's decision. |
| Current | The value used in the present schematic or plan. It may change. |
| Draft | A working assumption. Use it, but say in any finding that depends on it that it rests on a draft value. |
| TBD | Not decided. Do not invent a value. Report what the decision depends on. |

When the user changes a value, update it here, add a line to the change log at the end, and nowhere else. Other documents (design READMEs, index entries, reviews) quote these values with a reference to this file, so they can be checked against it later.

## 1. System

| Item | Value | Status | Notes |
|---|---|---|---|
| Sensor | GMOS gas sensor | Fixed | Electrical model and impedance not recorded here yet (TBD). |
| Detection method | Dual-phase (X and Y) lock-in with a switched +1/-1 demodulator | Current | Integrated lock-in ICs were rejected as hard to buy. |
| Front end | Instrumentation amplifier followed by Sallen-Key high-pass and low-pass filters | Current | Simulated separately from the demodulator so far. |
| Readout | VX and VY digitised by an ADC, relative to the demodulator reference | Draft | ADC type not chosen (TBD). |
| Excitation | Square wave synchronous with the reference | Draft | Drive circuit and sensor load TBD. |

## 2. Supply and reference

| Item | Value | Status | Notes |
|---|---|---|---|
| Supply | Single rail, 0 V to 5 V, for every part | Current | Power supply circuitry not decided yet, also still not sure if we use single rail or +-5V or other design. |

## 3. Frequencies

| Item | Value | Status | Notes |
|---|---|---|---|
| Frequency range of interest | 100 Hz to 10 kHz | Draft | None |
| Interference to reject | TBD | Draft | |

## 4. Signal levels

| Item | Value | Status | Notes |
|---|---|---|---|
| Sensor signal at the in-amp input | TBD | Draft | None |
| In-amp gain | 11 V/V | Current | RG = 5 kOhm (C-02). |
| Signal at the demodulator input | about 166 mV amplitude | Draft | 15 mV times the band-pass gain at `f_osc` (C-06). |
| Expected DC offset at the demodulator input | TBD | TBD | Depends on the in-amp and filter offsets. |
| Largest interference at the demodulator input | TBD | TBD | |

## 5. Performance targets

| Item | Value | Status | Notes |
|---|---|---|---|
| Amplitude accuracy | TBD | TBD | |
| Phase accuracy | TBD | TBD | |
| Resolution (smallest detectable change) | TBD | TBD | |
| Output bandwidth or settling time | Set by the output RC (tau = 0.1 s at present) | Current | Requirement TBD. |

## 6. Current parts

| Function | Part | Status | Notes |
|---|---|---|---|
| Demodulator op amp | OPAx192 | Current | Model in `vendor/sbom862f/`. |
| Demodulator switch | TMUX6136 (behavioural model SPDT_PREC) | Current, under review | Supply rating issue D-01. |
| Instrumentation amplifier | INA828 | Current, under review | Common-mode range issue D-02. |
| Demodulator resistors | 10 kOhm (R1, R2) | Current | Tolerance TBD. |
| Output filter | 10 kOhm and 10 uF | Current | |

## 7. Review limits

The design reviewer uses these limits to rate findings. They are provisional until the performance targets of section 5 are set.

| Item | Value | Status |
|---|---|---|
| Headroom margin to the swing limit of any part | 0.2 V | Draft |
| Major error threshold | 0.1 % of the expected output, or 1 deg of phase | Draft |

Severity levels:

| Level | Meaning |
|---|---|
| Critical | The circuit will not work, or a part is used outside its rating. Must be fixed before the next hardware step. |
| Major | The circuit works, but an error or risk exceeds the major error threshold above. |
| Minor | A small error, a missing margin or a better practice. |
| Note | Information or a simulation efficiency tip. |

## 8. Part sourcing rules

| Rule | Value | Status |
|---|---|---|
| Lifecycle | In production. Not NRND, not obsolete. | Draft |
| Stock at one distributor | At least 1000 units | Draft |
| Second source | Stock at a second distributor, or a pin-compatible second source | Draft |
| Packages | Hand-solderable preferred: SOIC, TSSOP, MSOP, SOT-23. Avoid WLCSP and QFN. | Draft |
| Simulation model | A PSpice or SPICE model must exist | Draft |
| Excluded | Single-IC lock-in parts (ADA2200, AD630 and similar), unless their stock has changed | Current |

## 9. Open requirement questions

- What is the sensor's impedance, and what does the excitation drive?
- What signal range and offset does the sensor produce?
- Which ADC, and is its input SAR or sigma-delta?
- What accuracy, phase accuracy and resolution does the gas measurement need?

## Change log

| Date | Change | By |
|---|---|---|
| 2026-10-27 | File created from the values that were spread over `CLAUDE.md` and the agent files. | Claude, at the user's request. Reviewed by user. |
