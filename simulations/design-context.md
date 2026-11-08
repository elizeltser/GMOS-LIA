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
| Front end | Instrumentation amplifier followed by K = 2 Sallen-Key high-pass and low-pass filters (FE-B) | Current | Board under simulation: LIA-AFE-Eval (decision E-1), netlist of 2026-11-07. Full chain in `circuits/afe_eval.cir`. |
| Readout | LIA-AFE-Eval: X_OUT and Y_OUT on SMA, centred on 0 V, no ADC on the board. LIA-Readout: ADC, type TBD | Current | |
| Excitation | Sine from the NUCLEO DAC through an MFB stage (gain -1/120) to one gate net, 5 mVpp default; square-wave references 0/3.3 V, Y delayed T/4 | Current | LIA-AFE-Eval requirements AN-1 to AN-3. Sensor load about 50 pF (SIM-19), sensor model TBD. |

## 2. Supply and reference

| Item | Value | Status | Notes |
|---|---|---|---|
| Supply | ±5 V analog (+5VA, -5VA) and +5VP from a bench input through a B5819W and 1 Ohm. +5VA = 5.0 V to 5.2 V (bench input set slightly above 5 V). TMUX6136 on ±15 V from a second bench input, on before the ±5 V input | Current | LIA-AFE-Eval DC-1 to DC-5, E-12. |
| Signal reference | GND for the in-amp REF, the filter returns and the demodulator zero | Current | No mid-supply reference on LIA-AFE-Eval. |

## 3. Frequencies

| Item | Value | Status | Notes |
|---|---|---|---|
| Excitation frequency | 518 Hz, band-pass -3 dB band 377 Hz to 711 Hz | Current | LIA-AFE-Eval AN-2 (LIA-Readout AN-1, AN-21). The older 100 Hz to 10 kHz range is replaced (requirements Q-8). |
| Interference to reject | TBD | Draft | |

## 4. Signal levels

| Item | Value | Status | Notes |
|---|---|---|---|
| Sensor signal at the in-amp input | 10 mV pk default in the simulations, linear range at least 50 mV pk | Draft | LIA-Readout AN-23a. Drain DC 50 mV to 250 mV, active-blind mismatch up to ±200 mV (AN-12a, AN-12b). |
| In-amp gain | 9.897 V/V | Current | RG = 5.62 kOhm (LIA-AFE-Eval AN-8, G = 10 nominal). Band-pass peak gain 39.59 V/V. |
| Signal at the demodulator input | about 396 mV pk at 10 mV pk drain signal, 1.98 V pk at 50 mV pk | Draft | 39.59 V/V times the drain signal. |
| Expected DC offset at the demodulator input | TBD | TBD | Depends on the in-amp and filter offsets. |
| Largest interference at the demodulator input | TBD | TBD | |

## 5. Performance targets

| Item | Value | Status | Notes |
|---|---|---|---|
| Amplitude accuracy | TBD | TBD | |
| Phase accuracy | TBD | TBD | |
| Resolution (smallest detectable change) | TBD | TBD | |
| Output bandwidth or settling time | Unity-gain Sallen-Key low-pass, 200 kOhm and 1.5 uF, two poles at 0.53 Hz (tau 0.3 s each) | Current | LIA-AFE-Eval AN-12, E-9. Requirement TBD. |

## 6. Current parts

| Function | Part | Status | Notes |
|---|---|---|---|
| Op amps (all stages) | OPA2196 | Current | TI model `OPAx196` in `nom_pspti.lib`. Earlier runs used OPAx192 (`vendor/sbom862f/`). |
| Demodulator switch | TMUX6136 on ±15 V (behavioural model SPDT_PREC) | Current | DI-01 is resolved by the ±15 V supply. |
| Instrumentation amplifier | INA828 on ±5 V | Current | DI-02 does not apply on ±5 V with drains at 50 mV to 250 mV. |
| Demodulator resistors | 10 kOhm 0.1 %, 10 ppm/K (R78, R79, R83, R84) | Current | |
| Output filter | 200 kOhm 0.1 % and 1.5 uF acrylic film 20 % | Current | |
| Drain path | R_D = 330 kOhm 0.1 %, drain node capacitance about 50 pF ± 10 % | Current | LIA-AFE-Eval AN-4a, SIM-12. |

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
| 2026-11-07 | Baseline moved to the LIA-AFE-Eval board (netlist of 2026-11-07): supply, reference, frequency, gains, op amps, switch supply, post-filter, drain path. | Claude, at the user's request (review A-04). |
